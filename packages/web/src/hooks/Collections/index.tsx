import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"; // Updated import
import { useApiClient } from "../../components/ApiClient";
import {
  AddressSuggestion,
  AssessmentStatus,
  CoordinatesResponse,
  CreateCollectionRequest,
  UpdateCollectionRequest,
} from "@aws-samples/cv-verification-api-client/src";

export const useGetAllCollections = () => {
  const apiClient = useApiClient();
  return useQuery({
    // Object syntax
    queryKey: ["collections"], // Array key
    queryFn: async () => {
      const response = await apiClient?.listCollectionsCollectionsGet();
      return response?.items.sort((a, b) => b.createdAt - a.createdAt) ?? [];
    },
    enabled: !!apiClient,
  });
};

// --- Get Coordinates by Address Hook ---
export const useGetCoordinatesByAddress = (address: string) => {
  const apiClient = useApiClient();
  return useQuery<CoordinatesResponse | null, Error>({
    // Specify return type and error type
    queryKey: ["coordinatesByAddress", address], // Query key includes the address
    queryFn: async () => {
      if (!address) {
        // Don't fetch if address is empty
        return null;
      }

      const response =
        await apiClient?.getCoordinatesCollectionsCoordinatesPost({
          // Corrected method name
          coordinatesRequest: { address },
        });
      // Check if response is valid before accessing coordinates
      if (!response) {
        console.error(
          "API client returned undefined for get coordinates by address"
        );
        return null; // Return null if response is undefined
      }
      return response; // Return the full response object containing coordinates
    },
    enabled: !!apiClient && !!address, // Only enable when client is ready and address is provided
    staleTime: Infinity, // Cache coordinates indefinitely as they rarely change
    gcTime: Infinity,
  });
};

export const useGetCollection = (collectionId?: string) => {
  const apiClient = useApiClient();
  return useQuery({
    // Object syntax
    queryKey: ["collection", collectionId],
    queryFn: async () => {
      if (!collectionId) return null;
      return await apiClient?.getCollectionCollectionsCollectionIdGet({
        collectionId,
      });
    },
    enabled: !!apiClient && !!collectionId,
  });
};

export const useCreateCollection = () => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    // Object syntax
    mutationFn: async (createCollectionRequest: CreateCollectionRequest) => {
      return await apiClient?.createCollectionCollectionsPost({
        createCollectionRequest,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["createCollection"] }); // Object syntax + Array key
    },
  });
};

export const useUpdateCollection = (collectionId?: string) => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    // Object syntax
    mutationFn: async (updateCollectionRequest: UpdateCollectionRequest) => {
      if (collectionId) {
        return await apiClient?.updateCollectionCollectionsCollectionIdPut({
          collectionId,
          updateCollectionRequest,
        });
      }
    },
    onSuccess: () => {
      // Removed unused parameters
      queryClient.invalidateQueries({ queryKey: ["collections"] }); // Object syntax + Array key
      if (collectionId) {
        queryClient.invalidateQueries({
          queryKey: ["collection", collectionId],
        }); // Object syntax
      }
    },
  });
};

export const useDeleteCollection = () => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    // Object syntax
    mutationFn: async (collectionId: string) => {
      return await apiClient?.deleteCollectionCollectionsCollectionIdDelete({
        collectionId,
      });
    },
    onSuccess: () => {
      // Invalidate and refetch the collections list query
      queryClient.invalidateQueries({ queryKey: ["collections"] }); // Object syntax + Array key
    },
  });
};

export const usePresignCollectionsFileUpload = (collectionId?: string) => {
  const apiClient = useApiClient();

  return useMutation({
    // Object syntax
    mutationFn: async ({
      // Removed duplicated parameter definition
      contentType,
      filename,
    }: {
      contentType: string;
      filename: string;
    }) => {
      if (!collectionId) return null;
      return await apiClient?.presignCollectionFileUploadCollectionsCollectionIdPresignUploadPost(
        {
          collectionId,
          contentType,
          filename,
        }
      );
    },
    // No onSuccess needed here usually
  });
};

export const useGetCollectionFilePresignedUrls = (collectionId?: string) => {
  const apiClient = useApiClient();
  return useQuery({
    // Object syntax
    // Ensure this query key matches the one used for invalidation in WorkOrderDetails
    queryKey: ["collection", collectionId, "files", "presignedUrls"],
    queryFn: async () => {
      if (!collectionId) return null;
      const response =
        await apiClient?.getCollectionFilePresignedUrlsCollectionsCollectionIdFilesPresignedUrlsGet(
          {
            collectionId,
          }
        );
      return response?.presignedUrls ?? {}; // Return the dictionary of URLs or empty object
    },
    enabled: !!apiClient && !!collectionId,
    // Optional: Add staleTime or cacheTime if needed
  });
};

export const useAddFileToCollection = (collectionId?: string) => {
  const apiClient = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    // Object syntax
    mutationFn: async (fileData: {
      id: string;
      createdAt: number; // Assuming API expects number, adjust if string
      s3Key: string; // Keep camelCase if API client expects it
      contentType: string;
      filename: string;
      description?: string; // Optional
      status?: AssessmentStatus;
      statusReasoning?: string; // Optional
    }) => {
      if (!collectionId) return null; // Or throw error
      // Ensure the structure of fileData matches AddFileRequest in the API client
      return await apiClient?.addFileToCollectionCollectionsCollectionIdFilesPost(
        {
          collectionId,
          addFileRequest: fileData, // Pass the data directly if it matches
        }
      );
    },
    onSuccess: () => {
      // Removed unused parameters

      // Also invalidate the presigned URLs query as new files were added
      if (collectionId) {
        queryClient.invalidateQueries({
          queryKey: ["collection", collectionId],
        }); // Object syntax
        // Ensure this query key matches the one used in useGetWorkOrderFilePresignedUrls
        queryClient.invalidateQueries({
          queryKey: ["collection", collectionId, "files", "presignedUrls"],
        });
      }
    }, // Removed trailing comma
  });
};

// --- Address Autocomplete Hook ---
export const useAddressAutocomplete = (query: string) => {
  const apiClient = useApiClient();
  return useQuery<AddressSuggestion[], Error>({
    // Specify return type and error type
    queryKey: ["addressAutocomplete", query], // Query key includes the search query
    queryFn: async () => {
      if (!query || query.length < 5) {
        // Don't fetch if query is too short or empty
        return [];
      }
      const response =
        await apiClient?.addressAutocompleteCollectionsAddressAutocompleteGet({
          query,
        });
      // Check if response is valid before accessing suggestions
      if (!response) {
        console.error("API client returned undefined for address autocomplete");
        return []; // Return empty array if response is undefined
      }
      return response.suggestions ?? []; // Return suggestions or empty array
    },
    enabled: !!apiClient && query.length >= 5, // Only enable when client is ready and query is long enough
    staleTime: 300000, // Cache suggestions for 5 minutes
    gcTime: 600000, // Keep data in cache for 10 minutes
  });
};
