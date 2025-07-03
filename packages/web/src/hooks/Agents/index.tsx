import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "../../components/ApiClient";
import {
  CreateAgentRequest,
  UpdateAgentRequest,
  Agent,
} from "@aws-samples/cv-verification-api-client/src";

export const useGetAllAgents = () => {
  const apiClient = useApiClient();
  return useQuery({
    queryKey: ["agents"],
    queryFn: async () => {
      const response = await apiClient?.getAgentsAgentsGet();
      return (
        response?.agents.sort((a: Agent, b: Agent) =>
          a.name.localeCompare(b.name)
        ) ?? []
      );
    },
    enabled: !!apiClient,
  });
};

export const useGetAgentsByVerificationJob = (verificationJobId: string) => {
  const apiClient = useApiClient();
  return useQuery({
    queryKey: ["agentsjob", verificationJobId],
    queryFn: async () => {
      const response =
        await apiClient?.getAgentsUsedInJobAgentsJobVerificationJobIdGet({
          verificationJobId,
        });
      return (
        response?.agents.sort((a: Agent, b: Agent) =>
          a.name.localeCompare(b.name)
        ) ?? []
      );
    },
    enabled: !!apiClient,
  });
};

export const useGetAgent = (agentId?: string) => {
  const apiClient = useApiClient();
  return useQuery({
    queryKey: ["agent", agentId],
    queryFn: async (): Promise<Agent | null> => {
      if (!agentId) return null;
      const response = await apiClient?.getAgentAgentsAgentIdGet({
        agentId,
      });
      return response || null;
    },
    enabled: !!apiClient && !!agentId,
  });
};

export const useCreateAgent = () => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (createAgentRequest: CreateAgentRequest) => {
      return await apiClient?.createAgentAgentsPost({
        createAgentRequest: createAgentRequest,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });
};

export const useUpdateAgent = (agentId?: string) => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (updateAgentRequest: UpdateAgentRequest) => {
      if (agentId) {
        return await apiClient?.updateAgentAgentsAgentIdPut({
          agentId,
          updateAgentRequest: updateAgentRequest,
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      if (agentId) {
        queryClient.invalidateQueries({
          queryKey: ["agent", agentId],
        });
      }
    },
  });
};

export const useDeleteAgent = () => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (agentId: string) => {
      return await apiClient?.deleteAgentAgentsAgentIdDelete({
        agentId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });
};
