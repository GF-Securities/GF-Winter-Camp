# -*- coding: utf-8 -*-
"""
把微信 H5 副本里的占位符换成真实部署地址。可反复运行（每次都从纯净模板重新生成）。

方案 A（只补抓取标签，不需要公众号）：
    python 一键配置.py --base https://h5.你的域名.com/winter2027

托管链接要求带访问参数时（如 WorkBuddy 发布的 ?sharecode=xxx），必须加 --query，
否则封面图会被 403 拦截、卡片没有图片：
    python 一键配置.py --base https://xxx.app.workbuddy.host --query sharecode=xxxx

方案 B（额外启用 JS-SDK 自定义分享）：
    python 一键配置.py --base https://h5.你的域名.com/winter2027 --appid wx你的AppID --sign https://api.你的域名.com/wx-sign
"""
import argparse
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "index.html")
TEMPLATE = os.path.join(HERE, "index.template.html")


def main():
    ap = argparse.ArgumentParser(description="微信 H5 转发版一键配置")
    ap.add_argument("--base", required=True, help="页面所在目录的 HTTPS 地址，末尾不要带斜杠")
    ap.add_argument("--appid", default="", help="公众号 AppID（方案 B 必填，与 --sign 同时给）")
    ap.add_argument("--sign", default="", help="后端签名接口地址（方案 B 必填，与 --appid 同时给）")
    ap.add_argument("--query", default="", help="访问参数，如 sharecode=xxx；封面与分享链接会自动带上")
    a = ap.parse_args()

    base = a.base.rstrip("/")
    q = "?" + a.query.lstrip("?") if a.query.strip() else ""
    low = base.lower()
    if any(x in low for x in ("127.0.0.1", "localhost", "file://", "0.0.0.0", "192.168.")):
        print("[错误] 不能填本地 / 内网地址：%s" % base)
        print("       微信服务器访问不到你电脑上的预览地址，抓不到 og:image，卡片必然没有图片。")
        print("       请填部署到公网后的 HTTPS 地址，形如 https://h5.你的域名.com/winter2027")
        return 1
    if not base.startswith("https://"):
        print("[提示] 建议使用 https:// 开头；http 地址微信抓图不稳定。")
    if bool(a.appid) != bool(a.sign):
        print("[错误] --appid 与 --sign 必须同时提供（或同时省略）。")
        return 1

    if not os.path.exists(TARGET):
        print("[错误] 找不到 index.html，请确认本脚本与 index.html 在同一目录。")
        return 1
    if not os.path.exists(TEMPLATE):
        shutil.copyfile(TARGET, TEMPLATE)
        print("√ 已保存未配置模板：index.template.html（之后可用它重置）")

    tpl = open(TEMPLATE, encoding="utf-8").read()
    if "__SHARE_BASE_URL__" not in tpl:
        print("[错误] index.template.html 不是纯净模板（占位符已丢失），可能是旧版本或已配置过的文件。")
        print("       请先重新运行 make_wx_h5.py 从最新主站 index.html 重建 H5 副本与模板，再执行本脚本。")
        return 1
    # 模板可能早于主站最近一次改版：用模板中是否残留主站已清除的旧口径来兜底提示
    if "中央指挥室" in tpl or "元始股" in tpl:
        print("[错误] index.template.html 仍是旧版内容（含已废弃的内部场所/产品名）。")
        print("       请先重新运行 make_wx_h5.py 重建 H5 副本与模板，再执行本脚本。")
        return 1

    s = tpl
    s = s.replace("__SHARE_BASE_URL__", base)
    # 托管站点若要求所有请求都带访问参数，og:image / og:url 也必须带上，
    # 否则微信单独抓封面时会拿到 403 —— 这是「转发没有图片」最隐蔽的一种原因。
    if q:
        s = s.replace(base + "/share_cover.png\"", base + "/share_cover.png" + q + "\"")
        s = s.replace(base + "/index.html\"", base + "/index.html" + q + "\"")
    s = s.replace("__SHARE_QUERY__", q)

    if a.appid:
        s = s.replace("__WX_APPID__", a.appid)
        s = s.replace("__WX_SIGN_URL__", a.sign)
        s = s.replace("sdkEnabled: false", "sdkEnabled: true")

    open(TARGET, "w", encoding="utf-8").write(s)

    # verify
    import re
    v = open(TARGET, encoding="utf-8").read()
    assert "__SHARE_BASE_URL__" not in v, "base 占位符未替换干净"
    assert "__SHARE_QUERY__" not in v, "query 占位符未替换干净"
    og = re.search(r'<meta property="og:image" content="([^"]+)"', v)
    cover = os.path.join(HERE, "share_cover.png")
    print("")
    print("√ 配置完成")
    print("  页面地址  :", base + "/index.html" + q)
    print("  og:image  :", og.group(1) if og else "× 未找到（请检查 index.html）")
    if q:
        print("  访问参数  :", q, "（封面与分享链接均已带上）")
    print("  封面文件  :", "√ share_cover.png 已就位（500×500 PNG）" if os.path.exists(cover)
          else "× 缺失！必须把 share_cover.png 与 index.html 放在同一目录一起上传")
    print("  方案      :", "B（JS-SDK 自定义卡片，已启用）" if a.appid else "A（微信抓取 meta 生成卡片）")
    if a.appid:
        print("  AppID     :", a.appid)
        print("  签名接口  :", a.sign)
    print("")
    print("★ 上传后必做两件事（否则卡片仍然没有图片）：")
    print("  1) 浏览器直接打开 " + (og.group(1) if og else base + "/share_cover.png" + q) + " 确认能看到图，")
    print("     不能是 404 / 403 / 需要登录；图片要与 index.html 放在同一目录。")
    print("     若站点要求 sharecode 等访问参数，封面地址也必须带同样的参数。")
    print("  2) 之前若已转发过该链接，微信抓取结果有缓存：")
    print("     用没发过该链接的微信号测试，或在链接后加 ?v=2 再转发一次。")
    print("")
    print("需要逐项体检线上配置，运行： python 分享卡片自检.py --page " + base + "/index.html" + q)
    return 0


if __name__ == "__main__":
    sys.exit(main())
