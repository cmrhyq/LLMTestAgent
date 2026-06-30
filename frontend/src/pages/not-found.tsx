import { Link, useNavigate } from "react-router-dom";
import { Compass, ArrowLeft, LayoutDashboard } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="flex h-full min-h-[60vh] flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent/10">
        <Compass className="h-8 w-8 text-accent" />
      </div>

      <div className="space-y-2">
        <p className="text-6xl font-bold tracking-tight text-foreground">404</p>
        <h1 className="text-xl font-semibold text-foreground">页面未找到</h1>
        <p className="mx-auto max-w-md text-sm text-muted-foreground">
          你访问的页面不存在或可能已被移动。请检查网址，或返回到已知的页面。
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
          返回上一页
        </Button>
        <Button asChild>
          <Link to="/dashboard">
            <LayoutDashboard className="h-4 w-4" />
            前往仪表盘
          </Link>
        </Button>
      </div>
    </div>
  );
}
