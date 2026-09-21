import time
import os
from selenium import webdriver


def main():
    print("=" * 40)
    print("DeepSeek 对话导出工具 (Edge版 - CDP + 自动找标签页)")
    print("=" * 40)

    # ==== 默认保存文件夹（可以改成你想要的位置）====
    SAVE_DIR = r"D:\对话存档"
    os.makedirs(SAVE_DIR, exist_ok=True)  # 文件夹不存在就自动创建

    print(f"默认保存位置: {SAVE_DIR}")
    default_name = "chat_log.txt"
    name_input = input(f"请输入文件名 (直接回车默认 {default_name}): ").strip()
    if not name_input:
        name_input = default_name
    if not name_input.endswith(".txt"):
        name_input += ".txt"
    file_name = os.path.join(SAVE_DIR, name_input)

    print(f"\n导出文件将保存为: {file_name}")
    print("⚠️ 请确保带 9222 端口的 Edge 里已经打开了 DeepSeek 对话页面。\n")

    # ==== CDP 连接模式 ====
    options = webdriver.EdgeOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    print("正在连接 Edge 浏览器，请稍候...")
    driver = webdriver.Edge(options=options)

    try:
        # ==== 遍历所有标签页，找到 DeepSeek 对话页面 ====
        target_handle = None
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            url = driver.current_url
            print(f"  检查标签页: {url}")
            if "chat.deepseek.com" in url and "/a/chat/s/" in url:
                target_handle = handle
                break

        if target_handle is None:
            print("❌ 没有找到 DeepSeek 对话标签页，请确认那个 Edge 里已打开对话页面。")
            return

        driver.switch_to.window(target_handle)
        print(f"✅ 已切换到对话页面: {driver.current_url}")

        print("已连接！正在等待页面加载...")
        time.sleep(5)

        print("正在加载完整历史记录（冲顶下滑）...")

        # ==== 找到真正的滚动容器 ====
        find_scroll_container = """
        const all = document.querySelectorAll('div, main, section');
        let best = null;
        let maxScroll = 0;
        for (const el of all) {
            const scrollH = el.scrollHeight;
            const clientH = el.clientHeight;
            if (scrollH > clientH + 100 && scrollH > maxScroll) {
                maxScroll = scrollH;
                best = el;
            }
        }
        if (best) {
            window.__scrollContainer = best;
            return { scrollHeight: best.scrollHeight, clientHeight: best.clientHeight };
        }
        return null;
        """

        info = driver.execute_script(find_scroll_container)
        if info:
            print(f"  找到滚动容器: scrollHeight={info['scrollHeight']}, clientHeight={info['clientHeight']}")
        else:
            print("  ⚠️ 没找到内部滚动容器，尝试用默认方式")

        # ==== 用真实 class 精确定位整条消息 ====
        extract_script = """
        const results = [];
        const nodes = document.querySelectorAll('div.fbb737a4, div.ds-assistant-message-main-content');
        
        for (const node of nodes) {
            const text = (node.innerText || '').trim();
            if (!text || text.length < 2) continue;
            
            let role = 'unknown';
            const cls = (node.className || '').toString();
            if (cls.includes('fbb737a4')) {
                role = 'user';
            } else if (cls.includes('ds-assistant-message-main-content')) {
                role = 'ai';
            }
            
            results.push({ role: role, text: text });
        }
        
        return results;
        """

        all_messages = []
        seen_texts = set()

        def collect_current():
            """抓当前 DOM 里的所有消息，累积到 all_messages，保持页面顺序"""
            try:
                msgs = driver.execute_script(extract_script)
                new_count = 0
                for m in msgs:
                    key = m['text']
                    if key not in seen_texts:
                        seen_texts.add(key)
                        all_messages.append(m)
                        new_count += 1
                return new_count
            except Exception:
                return 0

        # ==== 第一步：冲到最顶部，触发加载最老的消息 ====
        driver.execute_script("""
            if (window.__scrollContainer) {
                window.__scrollContainer.scrollTop = 0;
            } else {
                window.scrollTo(0, 0);
            }
        """)
        time.sleep(4)
        collect_current()
        print(f"  冲到顶部后，累积 {len(all_messages)} 条")

        last_height = driver.execute_script("""
            if (window.__scrollContainer) {
                return window.__scrollContainer.scrollHeight;
            }
            return document.body.scrollHeight;
        """)
        no_change_count = 0
        max_no_change = 10
        scroll_count = 0
        step = 2000

        # ==== 第二步：从顶部慢慢往下滚，让所有消息都出现过 ====
        while scroll_count < 500:
            current_scroll = driver.execute_script("""
                if (window.__scrollContainer) {
                    return window.__scrollContainer.scrollTop;
                }
                return window.pageYOffset;
            """)
            max_scroll = driver.execute_script("""
                if (window.__scrollContainer) {
                    return window.__scrollContainer.scrollHeight - window.__scrollContainer.clientHeight;
                }
                return document.body.scrollHeight - window.innerHeight;
            """)

            # 到底了就多等几轮再退出
            if current_scroll >= max_scroll - 10:
                no_change_count += 1
                collect_current()
                print(f"  [第{scroll_count+1}轮] 已到底部，等待加载 ({no_change_count}/{max_no_change}) | 累积 {len(all_messages)} 条")
                if no_change_count >= max_no_change:
                    break
                time.sleep(2)
            else:
                driver.execute_script(f"""
                    if (window.__scrollContainer) {{
                        window.__scrollContainer.scrollTop = window.__scrollContainer.scrollTop + {step};
                    }} else {{
                        window.scrollBy(0, {step});
                    }}
                """)
                no_change_count = 0
                time.sleep(1)

            # 每滑一段就抓一次
            new_count = collect_current()

            new_height = driver.execute_script("""
                if (window.__scrollContainer) {
                    return window.__scrollContainer.scrollHeight;
                }
                return document.body.scrollHeight;
            """)

            if new_height != last_height:
                print(f"  [第{scroll_count+1}轮] 高度 {last_height} → {new_height} | 新增 {new_count} 条，累积 {len(all_messages)} 条")
                last_height = new_height
                time.sleep(1)

            scroll_count += 1

        print(f"滚动结束，当前高度: {last_height}")
        print(f"历史记录加载完毕，累积 {len(all_messages)} 条消息，开始写入文件...")

        # ==== 写入文件 ====
        if all_messages:
            with open(file_name, "w", encoding="utf-8") as f:
                for m in all_messages:
                    if m['role'] == 'user':
                        f.write("【我】\n")
                    elif m['role'] == 'ai':
                        f.write("【AI】\n")
                    else:
                        f.write("【未知】\n")
                    f.write(m['text'] + "\n\n")
                    f.write("-" * 40 + "\n\n")

            abs_path = os.path.abspath(file_name)
            print(f"\n✅ 成功！共导出 {len(all_messages)} 条消息。")
            print(f"文件保存在: {abs_path}")
        else:
            print("\n❌ 没有抓到任何消息。")

    except Exception as e:
        print(f"\n❌ 出错了: {e}")
    finally:
        print("脚本执行结束。浏览器保持打开。")


if __name__ == "__main__":
    main()