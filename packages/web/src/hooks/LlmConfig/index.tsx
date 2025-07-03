import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "../../components/ApiClient";
import {
  SystemPromptRequest,
  ModelIdRequest,
  VerificationJobSecondPassRequest,
} from "@aws-samples/cv-verification-api-client/src";

// Hook to get the current system prompt
export const useGetSystemPrompt = () => {
  const apiClient = useApiClient();
  return useQuery({
    queryKey: ["llm-config", "system-prompt"],
    queryFn: async () => {
      return await apiClient?.getCurrentSystemPromptLlmConfigSystemPromptGet();
    },
    enabled: !!apiClient,
  });
};

// Hook to get the system prompt history
export const useGetSystemPromptHistory = (limit: number = 10) => {
  const apiClient = useApiClient();
  return useQuery({
    queryKey: ["llm-config", "system-prompt-history", limit],
    queryFn: async () => {
      return await apiClient?.getSystemPromptHistoryLlmConfigHistorySystemPromptGet(
        {
          limit,
        }
      );
    },
    enabled: !!apiClient,
  });
};

// Hook to update the system prompt
export const useUpdateSystemPrompt = () => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (systemPromptRequest: SystemPromptRequest) => {
      return await apiClient?.updateSystemPromptLlmConfigSystemPromptPost({
        systemPromptRequest,
      });
    },
    onSuccess: () => {
      // Invalidate and refetch the system prompt and history queries
      queryClient.invalidateQueries({
        queryKey: ["llm-config", "system-prompt"],
      });
      queryClient.invalidateQueries({
        queryKey: ["llm-config", "system-prompt-history"],
      });
    },
  });
};

// Hook to get the current model ID
export const useGetModelId = () => {
  const apiClient = useApiClient();
  return useQuery({
    queryKey: ["llm-config", "model-id"],
    queryFn: async () => {
      return await apiClient?.getCurrentModelIdLlmConfigModelIdGet();
    },
    enabled: !!apiClient,
  });
};

// Hook to get the model ID history
export const useGetModelIdHistory = (limit: number = 10) => {
  const apiClient = useApiClient();
  return useQuery({
    queryKey: ["llm-config", "model-id-history", limit],
    queryFn: async () => {
      return await apiClient?.getModelIdHistoryLlmConfigHistoryModelIdGet({
        limit,
      });
    },
    enabled: !!apiClient,
  });
};

// Hook to update the model ID
export const useUpdateModelId = () => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (modelIdRequest: ModelIdRequest) => {
      return await apiClient?.updateModelIdLlmConfigModelIdPost({
        modelIdRequest,
      });
    },
    onSuccess: () => {
      // Invalidate and refetch the model ID and history queries
      queryClient.invalidateQueries({ queryKey: ["llm-config", "model-id"] });
      queryClient.invalidateQueries({
        queryKey: ["llm-config", "model-id-history"],
      });
    },
  });
};

export const useGetVerificationJobSecondPass = () => {
  const apiClient = useApiClient();
  return useQuery({
    queryKey: ["llm-config", "second-pass"],
    queryFn: async () => {
      return await apiClient?.getJobSecondPassLlmConfigSecondPassGet();
    },
    enabled: !!apiClient,
  });
};

export const useUpdateVerificationJobSecondPass = () => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: VerificationJobSecondPassRequest) => {
      return await apiClient?.updateJobSecondPassLlmConfigSecondPassPost({
        verificationJobSecondPassRequest: request,
      });
    },
    onSuccess: () => {
      // Invalidate and refetch the model ID and history queries
      queryClient.invalidateQueries({
        queryKey: ["llm-config", "second-pass"],
      });
    },
  });
};
