import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout/app-layout";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      {
        path: "dashboard",
        lazy: async () => {
          const { default: Component } = await import("./pages/dashboard");
          return { Component };
        },
      },
      {
        path: "projects/:id",
        lazy: async () => {
          const { default: Component } = await import("./pages/project-detail");
          return { Component };
        },
      },
      {
        path: "projects/:id/endpoints",
        element: <Navigate to=".." replace relative="path" />,
      },
      {
        path: "projects/:id/environments",
        element: <Navigate to=".." replace relative="path" />,
      },
      {
        path: "projects/:id/runs",
        element: <Navigate to=".." replace relative="path" />,
      },
      {
        path: "runs/:id",
        lazy: async () => {
          const { default: Component } = await import("./pages/run-detail");
          return { Component };
        },
      },
      {
        path: "workflows/parse",
        lazy: async () => {
          const { default: Component } = await import("./pages/workflow-parse");
          return { Component };
        },
      },
      {
        path: "workflows/run",
        lazy: async () => {
          const { default: Component } = await import("./pages/workflow-run");
          return { Component };
        },
      },
      {
        path: "reports",
        lazy: async () => {
          const { default: Component } = await import("./pages/reports");
          return { Component };
        },
      },
      {
        path: "reports/:id",
        lazy: async () => {
          const { default: Component } = await import("./pages/report-view");
          return { Component };
        },
      },
    ],
  },
]);
