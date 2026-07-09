import { useState } from "react";
import * as AccordionPrimitive from "@radix-ui/react-accordion";
import { ChevronDown, Folder, PlusCircle } from "lucide-react";
import { toast } from "sonner";
import { useProjects } from "@/hooks/use-projects";
import { getMockSpaceItems } from "@/lib/mock/space-items";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { cn } from "@/lib/utils";
import { Accordion, AccordionContent, AccordionItem } from "@/components/ui/accordion";

function SpacesSkeleton() {
  return (
    <div className="space-y-2 px-3 py-2">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-7 animate-pulse rounded-md bg-muted" />
      ))}
    </div>
  );
}

interface ProjectAccordionItemProps {
  projectId: string | number;
  projectName: string;
}

function ProjectAccordionItem({ projectId, projectName }: ProjectAccordionItemProps) {
  const items = getMockSpaceItems(projectId);

  return (
    <AccordionItem value={String(projectId)} className="border-none">
      <AccordionPrimitive.Header className="flex">
        <AccordionPrimitive.Trigger
          className={cn(
            "group flex flex-1 items-center gap-1 rounded-md px-2 py-1.5 text-sm font-medium transition-colors hover:bg-muted hover:no-underline [&[data-state=open]_.project-chevron]:rotate-180"
          )}
        >
          <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="min-w-0 flex-1 truncate text-left text-foreground">{projectName}</span>
          <ChevronDown className="project-chevron h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform duration-200" />
          <span
            className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              aria-label="新建对话"
              className="rounded p-0.5 text-muted-foreground hover:bg-background hover:text-foreground"
              onClick={(e) => {
                e.stopPropagation();
                toast.info("新建对话功能即将上线");
              }}
            >
              <PlusCircle className="h-3.5 w-3.5" />
            </button>
          </span>
        </AccordionPrimitive.Trigger>
      </AccordionPrimitive.Header>
      <AccordionContent className="pb-1 pt-0">
        <ul className="space-y-0.5 pl-6">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-sm text-foreground/80 transition-colors hover:bg-muted hover:text-foreground"
                onClick={() => toast.info("对话历史功能即将上线")}
              >
                <span className="min-w-0 flex-1 truncate">{item.title}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatRelativeTime(item.updatedAt)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </AccordionContent>
    </AccordionItem>
  );
}

export function SpacesSection() {
  const [sectionOpen, setSectionOpen] = useState(true);
  const { data, isLoading, isError } = useProjects({ page_size: 100, status: 1 });

  const projects = data?.items ?? [];
  const total = data?.total ?? projects.length;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <button
        type="button"
        className="flex w-full shrink-0 items-center gap-1 px-5 py-3 text-left"
        onClick={() => setSectionOpen((open) => !open)}
        aria-expanded={sectionOpen}
      >
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform duration-200",
            !sectionOpen && "-rotate-90"
          )}
        />
        <span className="text-[11px] font-medium text-muted-foreground">空间 ({total})</span>
      </button>

      {sectionOpen && (
        <div className="spaces-scroll min-h-0 flex-1 px-3 pb-4">
          {isLoading && <SpacesSkeleton />}

          {isError && <p className="px-2 py-2 text-xs text-destructive">加载空间列表失败</p>}

          {!isLoading && !isError && projects.length === 0 && (
            <p className="px-2 py-2 text-xs text-muted-foreground">
              暂无空间，请先在仪表盘创建项目
            </p>
          )}

          {!isLoading && !isError && projects.length > 0 && (
            <Accordion type="multiple" className="space-y-0.5">
              {projects.map((project) => (
                <ProjectAccordionItem
                  key={project.id}
                  projectId={project.id}
                  projectName={project.name}
                />
              ))}
            </Accordion>
          )}
        </div>
      )}
    </div>
  );
}
