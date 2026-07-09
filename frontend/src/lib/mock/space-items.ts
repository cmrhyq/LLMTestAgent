export interface SpaceItem {
  id: string;
  title: string;
  updatedAt: string;
}

function daysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString();
}

const MOCK_ITEMS_POOL: Omit<SpaceItem, "id">[] = [
  { title: "这个项目里要增加chrom...", updatedAt: daysAgo(1) },
  { title: "帮我写登录接口测试用例", updatedAt: daysAgo(2) },
  { title: "分析用户注册流程的安全风险", updatedAt: daysAgo(5) },
  { title: "生成支付接口的边界测试", updatedAt: daysAgo(17) },
  { title: "检查 API 鉴权逻辑是否完整", updatedAt: daysAgo(3) },
];

export function getMockSpaceItems(projectId: string | number): SpaceItem[] {
  const seed = String(projectId)
    .split("")
    .reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const count = 2 + (seed % 3);

  return MOCK_ITEMS_POOL.slice(0, count).map((item, index) => ({
    ...item,
    id: `${projectId}-${index}`,
  }));
}
