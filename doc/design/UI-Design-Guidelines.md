# LLMTestAgent 页面设计准则

> 版本：v0.0.1（对应当前前端实现）
> 技术栈：Tailwind CSS v4 + shadcn/ui
> 令牌来源：[`frontend/src/index.css`](../../frontend/src/index.css)、[`frontend/tailwind.config.ts`](../../frontend/tailwind.config.ts)

---

## 一、设计目标

整体风格参考现代 IDE / 工具类产品（如 Cursor）：**白底、轻灰侧栏、细边框、低对比阴影、留白充足**。界面应感觉干净、专业、不喧宾夺主，让测试数据与工作流内容成为视觉焦点。

核心原则：

1. **层次靠边框与阴影，不靠大面积色块** — 容器以 1px 浅灰边框 + 轻阴影区分，避免整块深灰背景。
2. **中性色为主，语义色点缀** — 页面 90% 为白/灰；绿、蓝、红仅用于状态、链接、主操作。
3. **语义化令牌优先** — 使用 `bg-background`、`text-muted-foreground` 等令牌；页面层避免硬编码 `#ebebeb` 等（Sidebar 导航的 `blue-50` / `blue-100` 为既定例外）。
4. **组件复用优先** — 新页面应组合 `components/ui/*` 与 `components/shared/*`，而非重复写样式。

---

## 二、色彩体系

### 2.1 中性色（Light 模式）

| 令牌 | 色值 | 用途 |
|------|------|------|
| `background` | `#FFFFFF` | 页面主背景、主内容区 |
| `sidebar` | `#F7F7F5` | 侧边栏背景 |
| `card` / `popover` / `input` | `#FFFFFF` | 卡片、弹层、输入框 |
| `foreground` | `#1A1A1A` | 标题、正文主色 |
| `muted` | `#F5F5F5` | hover 背景、Tabs 轨道、次要容器 |
| `secondary` | `#EBEBEB` | 略深 hover、secondary 按钮 |
| `muted-foreground` | `#737373` | 说明文字、表头、占位符 |
| `border` | `#E8E8E8` | 容器边框、分隔线 |
| `border-subtle` | `#F0F0F0` | 表格行分隔等更弱的分割 |

### 2.2 语义色（产品逻辑）

| 令牌 | 色值 | 用途 |
|------|------|------|
| `primary` | `#1A7F37` | 主按钮、启用状态、成功类强调 |
| `accent` | `#0969DA` | 链接、信息类强调、focus 环 |
| `destructive` | `#CF222E` | 删除、错误、危险操作 |
| `success` | `#1A7F37` | 通过、GET 等方法 Badge |
| `warning` | `#9A6700` | 警告、PUT 等方法 Badge |
| `info` | `#0969DA` | 信息提示、POST 等方法 Badge |

### 2.3 表面 tint（`surface-*`）

用于统计卡图标背景等小面积点缀，**不可用作整页或大区块背景**：

- `surface-primary` / `surface-accent` / `surface-success` / `surface-warning`
- Light 模式：`color-mix(..., 10%, transparent)`

### 2.4 用色禁忌

- 禁止将 `card`、`muted`、`secondary` 设为相同色值导致层次消失。
- 禁止在页面中硬编码 `teal-500`、`emerald-500` 等 Tailwind 默认色；统一用语义令牌。
- 禁止在主内容区使用 `bg-blue-50` 等 tint 作为容器背景。

**例外：** Sidebar 导航项的选中 / hover 态保留淡蓝 tint（见 [5.2 Sidebar 规范](#52-sidebar-规范)），便于在侧栏内快速识别当前路由。

---

## 三、字体与排版

### 3.1 字体族

```css
-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif
```

### 3.2 层级规范

| 元素 | 类名建议 | 说明 |
|------|----------|------|
| 页面标题 | `text-2xl font-semibold tracking-tight` | 如「仪表盘」 |
| 区块标题 | `text-lg font-semibold` | 如「项目」「快捷操作」 |
| 卡片标题 | `text-sm font-medium text-muted-foreground` | 统计指标名称 |
| 正文 | `text-sm` | 默认内容 |
| 辅助说明 | `text-sm text-muted-foreground` | 副标题、描述 |
| 侧栏分组 | `text-[11px] font-medium text-muted-foreground` | 「工作流」「结果」 |
| 等宽数据 | `font-mono text-xs` | URL、代码片段 |

### 3.3 字重

- 默认以 **Regular / Medium** 为主；`font-bold` 仅用于关键数字（如统计值可用 `font-semibold`）。
- 避免同一视口内过多粗体，保持轻量感。

---

## 四、圆角、边框与阴影

### 4.1 圆角

| 令牌 | 值 | 适用 |
|------|-----|------|
| `rounded-sm` | 6px | 小元素 |
| `rounded-md` / `rounded-lg` | 8–10px | 按钮、导航项 |
| `rounded-xl` | 12px | 卡片、表格容器、Composer 输入框 |
| `rounded-full` | 50% | 胶囊工具按钮、圆形 FAB |

### 4.2 边框

- 标准容器：`border border-border`（1px，`#E8E8E8`）。
- 不再使用粗边框（2px+）或高对比色边框作为主要分隔手段。
- 表格行：`border-border-subtle`；区块顶/底：`border-border`。

### 4.3 阴影

定义于 `tailwind.config.ts`，按 elevation 选用：

| 类名 | 场景 |
|------|------|
| `shadow-xs` | 卡片、outline 按钮、输入框默认态 |
| `shadow-card` | Composer 输入区、需轻微浮起的面板 |
| `shadow-elevated` | 侧栏展开 FAB、Composer focus 态 |
| `shadow-popover` | Dropdown、Tooltip 弹层 |
| `shadow-input` | Input / Textarea focus 态（蓝色光晕） |

**原则：** 阴影透明度低（2%–8%），blur 偏大；避免「重阴影 + 深灰底」叠加。

---

## 五、布局结构

### 5.1 应用骨架

```
┌─────────────┬──────────────────────────────┐
│  Sidebar    │  Main (bg-background, p-6)   │
│  250px      │                              │
│  bg-sidebar │  <Outlet /> 页面内容          │
│  border-r   │                              │
└─────────────┴──────────────────────────────┘
```

- 无顶部 Header Nav；品牌与折叠控制均在 Sidebar 内。
- Sidebar 收起宽度为 0，带 300ms 宽度过渡；左上角圆形按钮展开。
- 主内容区统一 `p-6`，页面内区块间距 `space-y-8`。

### 5.2 Sidebar 规范

- 背景：`bg-sidebar`
- 右边框：`border-r border-border`
- 品牌区：Logo + 产品名 + 版本号（`text-[10px] text-muted-foreground`）
- 导航项（`NavLink`）— **侧栏内唯一允许使用淡蓝 tint 的区域**：
  - 默认：`border-l-2 border-transparent text-muted-foreground`
  - Hover：`hover:bg-blue-100 hover:text-foreground`
  - 选中：`border-l-2 border-accent bg-blue-50 font-medium text-foreground`
  - 布局：`rounded-md px-3 py-1.5 gap-2 text-sm`
- 图标：`lucide-react`，尺寸 `h-4 w-4`

### 5.3 页面内容区

- 典型结构：页面标题 → 统计/快捷区 → 主列表/表单。
- 列表页优先使用 `DataTable`；表单页使用 `Card` 包裹。
- 对话/工作流页 Composer 居中，`max-w-3xl`。

---

## 六、组件使用准则

### 6.1 Card

```tsx
// 默认：白底 + 细边框 + 轻阴影
<Card>...</Card>
// 类：rounded-xl border border-border bg-card shadow-xs
```

- 统计卡可在图标区使用 `bg-surface-*` 小色块，Card 本身保持白底。
- 不要去掉边框仅靠阴影，也不要使用深灰 `bg-card` 铺满主内容区。

### 6.2 Button

| Variant | 场景 |
|---------|------|
| `default` | 主操作（运行测试、提交）— 绿色 `primary` |
| `outline` | 次要操作 — 白底 + 边框 + `shadow-xs` |
| `ghost` | 表格行内、工具栏图标按钮 |
| `secondary` | 低强调填充按钮 |
| `destructive` | 删除确认 |
| `link` | 行内文字链（优先用 `<Link className="text-accent">`） |

- 默认高度 `h-8`；圆角 `rounded-lg`。
- 工具栏内小按钮可用 `rounded-full` 胶囊形态（见 Composer）。

### 6.3 Input / Textarea

- `rounded-lg border border-border bg-input shadow-xs`
- Focus：`focus-visible:border-accent/40 focus-visible:shadow-input`
- 不使用 focus 时的大幅 ring 或深色边框跳变。

### 6.4 DataTable

- 容器：`rounded-xl border border-border bg-background shadow-xs`
- 表头：`bg-muted/60` + `border-b border-border`
- 行 hover：`hover:bg-muted`；行分隔：`border-border-subtle`
- 分页按钮：`rounded-lg border border-border shadow-xs`

### 6.5 Composer（工作流 / 安全对话）

参考 Cursor 中央输入框：

```tsx
<div className="rounded-xl border border-border bg-background px-3 py-2.5 shadow-card
                focus-within:border-accent/30 focus-within:shadow-elevated">
  <textarea className="bg-transparent ..." />
  {/* 工具栏：rounded-full 胶囊按钮 */}
</div>
```

- 工具按钮：`rounded-full border border-border bg-background shadow-xs hover:bg-muted`
- 附件标签：`rounded-full bg-muted`

### 6.6 Badge 与状态

- HTTP 方法、测试状态使用 `HttpMethodBadge` / `StatusBadge`，语义色背景 10% 透明度级别。
- 项目状态等业务 Badge 使用 shadcn `Badge`：`default`（启用）/ `secondary`（未启用）。

### 6.7 链接

- 全局 `<a>` 默认 `color: accent`；表格内链接：`font-medium text-accent hover:text-accent/80`
- 导航链接使用 `NavLink`，**不要** 依赖全局下划线样式。

---

## 七、间距与密度

| 场景 | 建议 |
|------|------|
| 页面级垂直间距 | `space-y-8` |
| 卡片网格 | `grid gap-4 md:grid-cols-3` |
| 卡片内边距 | `p-6`（CardHeader / CardContent 默认） |
| 侧栏导航项 | `px-3 py-1.5`，项间距 `gap-0.5` |
| 分组标题上间距 | `mt-5 mb-1` |

保持「可呼吸」—— 组件内部 padding 充足，避免元素贴边。

---

## 八、图标与交互

- 图标库：**Lucide React**，线型图标，默认 `h-4 w-4`。
- Hover：背景变为 `bg-muted`，文字 `text-foreground`；过渡 `transition-colors`。
- 禁用：`disabled:opacity-50 disabled:cursor-not-allowed`。
- 折叠动画：Sidebar 宽度 `duration-300 ease-in-out`；内容透明度 `duration-200`。

---

## 九、暗色模式

- 令牌在 `.dark` 下于 `index.css` 统一覆盖，组件无需写双份颜色。
- 新增页面/组件时**只使用语义类名**，暗色模式自动生效。
- 暗色下 `sidebar` 为 `#12161C`，仍保持「侧栏略深、主区更深」的层次，而非纯黑一片。

---

## 十、新页面检查清单

新增或改版页面时，请确认：

- [ ] 未硬编码 Tailwind 调色板色（侧栏 NavLink 的 `blue-50` / `blue-100` 除外）
- [ ] 容器使用 `border-border` + 适当 `shadow-*`，而非纯 `border-0` 或纯深灰底
- [ ] 标题、说明文字层级符合第三节规范
- [ ] 主操作使用 `Button default`，次要使用 `outline` / `ghost`
- [ ] 列表使用 `DataTable`，未重复实现表格样式
- [ ] 链接与状态色使用 `accent` / `primary` / `destructive` / `success` 语义令牌
- [ ] 侧栏相关改动不破坏 250px 宽度与折叠行为
- [ ] 通过 `npm run type-check`

---

## 十一、相关文件索引

| 类型 | 路径 |
|------|------|
| 色彩与主题令牌 | `frontend/src/index.css` |
| 阴影 / 圆角结构令牌 | `frontend/tailwind.config.ts` |
| 应用布局 | `frontend/src/components/layout/app-layout.tsx` |
| 侧栏 | `frontend/src/components/layout/sidebar.tsx` |
| UI 基元 | `frontend/src/components/ui/*` |
| 表格 | `frontend/src/components/shared/data-table.tsx` |
| 参考页面 | `frontend/src/pages/dashboard.tsx` |
| Composer 参考 | `frontend/src/pages/run/workflow-run.tsx` |

---

## 十二、演进说明

本准则随前端实现迭代。若需调整全局风格，**优先改令牌层**（`index.css` + `tailwind.config.ts`），再改基元组件，最后才改个别页面。单次改版避免同时改动布局、配色、阴影三套体系，以便 review 与回退。
