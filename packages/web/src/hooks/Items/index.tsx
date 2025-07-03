import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "../../components/ApiClient";
import {
  CreateItemRequest,
  UpdateItemRequest,
} from "@aws-samples/cv-verification-api-client/src";

export const useGetAllItems = () => {
  const apiClient = useApiClient();
  return useQuery({
    queryKey: ["items"], // Query key must be an array
    queryFn: async () => {
      const response = await apiClient?.getItemsItemsGet();
      return (
        response?.items.sort((a, b) =>
          `${a.name}${a.description}`.localeCompare(`${b.name}${b.description}`)
        ) ?? []
      );
    },
    // Removed extra brace here
    enabled: !!apiClient,
  });
};

export const useGenerateUploadPresignedUrls = () => {
  const apiClient = useApiClient();
  return useMutation({
    mutationKey: ["uploadUrls"], // Mutation key must be an array
    mutationFn: async (filenames: string[]) => {
      return await apiClient?.generateUploadUrlsItemsUploadurlsPost({
        generateUploadUrlsRequest: { filenames },
      });
    },
  });
};

export const useGenerateDownloadPresignedUrls = () => {
  const apiClient = useApiClient();
  return useMutation({
    mutationKey: ["downloadUrls"], // Mutation key must be an array
    mutationFn: async (s3Keys: string[]) => {
      return await apiClient?.generateDownloadUrlItemsDownloadurlsPost({
        requestBody: s3Keys,
      });
    },
  });
};

export const useTestLabelRules = () => {
  const apiClient = useApiClient();
  return useMutation({
    mutationKey: ["testLabelRules"], // Mutation key must be an array
    mutationFn: async (request: { imageS3Keys: string[] }) => {
      return await apiClient?.itemLabelFilteringRuleTestItemsTestLabelPost({
        testLabelFilteringRuleRequest: {
          imageS3Keys: request.imageS3Keys,
        },
      });
    },
  });
};

export const useTestDescriptionPrompt = () => {
  const apiClient = useApiClient();
  return useMutation({
    mutationKey: ["testDescriptionPromopt"],
    mutationFn: async (request: {
      description: string;
      imageS3Keys: string[];
      agentIds?: string[];
    }) => {
      return await apiClient?.itemDescriptionFilterPromptTestItemsTestPromptPost(
        {
          testDescriptionFilterPromptRequest: {
            description: request.description,
            imageS3Keys: request.imageS3Keys,
            agentIds: request.agentIds,
          },
        }
      );
    },
  });
};

export const useGetItem = (itemId?: string) => {
  const apiClient = useApiClient();
  return useQuery({
    queryKey: ["item", itemId], // Already an array, good
    queryFn: async () => {
      if (!itemId) return null;
      return await apiClient?.getItemItemsItemIdGet({ itemId });
    },
    enabled: !!apiClient && !!itemId,
  });
};

export const useCreateItem = () => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (createItemRequest: CreateItemRequest) => {
      return await apiClient?.createItemItemsPost({ createItemRequest });
    },
    onSuccess: () => {
      // Invalidate and refetch the Items list query
      queryClient.invalidateQueries({ queryKey: ["items"] }); // Use object with queryKey
    },
  });
};

export const useUpdateItem = (itemId?: string) => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (updateItemRequest: UpdateItemRequest) => {
      if (itemId) {
        return await apiClient?.updateItemItemsItemIdPut({
          itemId,
          updateItemRequest,
        });
      }
    },
    onSuccess: () => {
      // Removed unused parameters: data, variables, context
      queryClient.invalidateQueries({ queryKey: ["items"] });
      if (itemId) {
        queryClient.invalidateQueries({ queryKey: ["items", itemId] });
      }
    },
  });
};

export const useDeleteItem = () => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (itemId: string) => {
      return await apiClient?.deleteItemItemsItemIdDelete({ itemId });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["items"] });
    }, // Removed trailing comma
  });
};
