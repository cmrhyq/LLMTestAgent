type ResourceId = string | number;

function createResourceKeys<const TPrefix extends string>(prefix: TPrefix) {
  return {
    all: [prefix] as const,
    list: (params?: unknown) => [prefix, "list", params] as const,
    detail: (id: ResourceId) => [prefix, "detail", id] as const,
  };
}

export const queryKeys = {
  spaces: createResourceKeys("spaces"),
  endpoints: createResourceKeys("endpoints"),
  environments: createResourceKeys("environments"),
  testRuns: createResourceKeys("test-runs"),
  reports: createResourceKeys("reports"),
  conversations: {
    ...createResourceKeys("conversations"),
    messages: (id: ResourceId | null | undefined) => ["conversations", "messages", id] as const,
  },
};

export type ResourceQueryKeys = ReturnType<typeof createResourceKeys>;
