import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout/app-layout";
import ErrorPage from "./pages/error/error-page.tsx";
import NotFoundPage from "./pages/error/not-found.tsx";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      {
        errorElement: <ErrorPage />,
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
            path: "spaces",
            lazy: async () => {
              const { default: Component } = await import("./pages/space/spaces.tsx");
              return { Component };
            },
          },
          {
            path: "spaces/:id",
            lazy: async () => {
              const { default: Component } = await import("./pages/space/space-detail.tsx");
              return { Component };
            },
          },
          {
            path: "spaces/:id/endpoints",
            element: <Navigate to=".." replace relative="path" />,
          },
          {
            path: "spaces/:id/environments",
            element: <Navigate to=".." replace relative="path" />,
          },
          {
            path: "spaces/:id/runs",
            element: <Navigate to=".." replace relative="path" />,
          },
          {
            path: "runs/:id",
            lazy: async () => {
              const { default: Component } = await import("./pages/run/run-detail.tsx");
              return { Component };
            },
          },
          {
            path: "workflows/run",
            element: <Navigate to="/workflows/chat" replace />,
          },
          {
            path: "workflows/chat",
            lazy: async () => {
              const { default: Component } = await import("./pages/run/security-chat.tsx");
              return { Component };
            },
          },
          {
            path: "reports",
            lazy: async () => {
              const { default: Component } = await import("./pages/report/reports.tsx");
              return { Component };
            },
          },
          {
            path: "reports/:id",
            lazy: async () => {
              const { default: Component } = await import("./pages/report/report-view.tsx");
              return { Component };
            },
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
]);
