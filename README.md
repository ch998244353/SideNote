# 侧笺 SideNote

一款轻量、常驻桌面、支持贴边停靠的 Windows 便签与待办工具。

[下载最新版](https://github.com/ch998244353/SideNote/releases/latest) · [查看更新记录](https://github.com/ch998244353/SideNote/releases)

![SideNote 功能总览](docs/images/overview.png)

## 功能

- 悬浮入口：左键打开待办面板，右键立即新建便签。
- 桌面便签：自由移动、调整大小，并自动保存内容和位置。
- 展开与收缩：便签可收缩为标题标签，需要时一键恢复。
- 贴边停靠：把便签拖到屏幕边缘，减少对桌面的遮挡。
- 待办管理：添加、完成、删除和拖动排序待办事项。
- 七种主题：雨蓝、石墨、暖黄、墨黑、彩色玻璃、云纸和麦纸。
- 外观设置：可调整入口大小、标签大小、待办文字和便签文字。
- 启动与纸张：支持开机启动，并可单独开启或关闭便签横线。
- 空标题：便签名称删除后会保持为空，不再自动恢复为“新便签”。
- 本地存储：数据只保存在本机，不依赖账号或网络服务。

## 功能展示

<table>
  <tr>
    <td width="50%" align="center">
      <img src="docs/images/settings-themes.png" alt="主题和外观设置">
      <br><strong>主题、字号、开机启动与横线开关</strong>
    </td>
    <td width="50%" align="center">
      <img src="docs/images/quick-create.png" alt="右键悬浮入口新建便签">
      <br><strong>右键悬浮入口，立即创建新便签</strong>
    </td>
  </tr>
</table>

![便签展开、收缩和贴边停靠](docs/images/dock-and-collapse.png)

## 下载与使用

1. 前往 [Releases](https://github.com/ch998244353/SideNote/releases/latest) 下载 `SideNote.exe`。
2. 双击运行，无需安装。
3. 左键单击悬浮入口打开待办面板，右键单击直接创建便签。
4. 单击便签标题栏的 `−` 可收缩；拖动便签到屏幕边缘可停靠。
5. 外观设置、开机启动和横线开关都在齿轮按钮中。

应用数据保存在：

```text
%LOCALAPPDATA%\SideNote\data.json
```

删除这个文件会清空便签、待办和设置，请在操作前自行备份。

## 从源码运行

当前构建依赖 Python 3.14，因为恢复得到的 `marshal` 主程序代码与 Python 小版本绑定。

```powershell
python src\side_note.pyw
```

## 测试与构建

```powershell
python -m unittest discover -s tests -v
python -m pip install -r requirements-build.txt
.\build.ps1
```

构建产物位于 `dist\SideNote.exe`。

## 项目结构

```text
assets/                       玻璃主题运行时素材
docs/images/                  项目展示图
src/side_note.pyw             可读启动器与功能补丁层
src/original_side_note.marshal 恢复得到的原主程序代码对象
tests/                        补丁行为测试
build.ps1                     Windows 一键构建脚本
```

## 源码状态（重要）

这个仓库是从现有 SideNote 可执行文件恢复并继续维护的版本。原始、完整的 `.pyw` 主程序源码不在当前工作区，因此仓库保留了恢复得到的 `src/original_side_note.marshal`，并通过可读的 `src/side_note.pyw` 补丁层修复和扩展功能。

当前版本可以运行、测试和重新构建，但主程序核心还不是完整可读源码。后续维护应逐步把恢复代码迁回普通 Python 源文件；在完成之前，不应把本仓库描述为完整源码复原版。

## 隐私

SideNote 不包含联网、遥测或云同步逻辑。README 中的展示图使用隔离的演示数据生成，不包含真实便签或桌面内容。

## 许可证

[MIT License](LICENSE)
