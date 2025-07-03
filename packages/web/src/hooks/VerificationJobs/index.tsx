import { useState, useEffect, useCallback } from "react";
import {
  VerificationJob,
  CreateVerificationJobRequest,
  UpdateVerificationJobRequest,
  VerificationJobLogEntry,
  VerificationJobDto, // Import the log entry type
} from "@aws-samples/cv-verification-api-client/src";
import { useApiClient } from "../../components/ApiClient";

/**
 * Hook to fetch a list of verification jobs.
 *
 * @returns An object containing the list of jobs, loading state, error state, and a refetch function.
 */
export const useVerificationJobs = () => {
  const apiClient = useApiClient();
  const [jobs, setJobs] = useState<VerificationJobDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null); // Store error message string

  const fetchJobs = useCallback(async () => {
    if (!apiClient) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response =
        await apiClient.listVerificationJobsVerificationJobsGet();
      setJobs(response.sort((a, b) => b.createdAt - a.createdAt) || []);
    } catch (err) {
      console.error("Failed to fetch verification jobs:", err);
      setError(
        err instanceof Error ? err.message : "An unknown error occurred"
      );
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  return { jobs, loading, error, refetch: fetchJobs };
};

/**
 * Hook to fetch a single verification job by its ID.
 *
 * @param jobId The ID of the verification job to fetch. If undefined, no fetch occurs.
 * @returns An object containing the job details, loading state, error state, and a refetch function.
 */
export const useVerificationJob = (jobId?: string) => {
  const apiClient = useApiClient();
  const [job, setJob] = useState<VerificationJobDto | null>(null);
  const [loading, setLoading] = useState(true); // Tracks initial load
  const [isPolling, setIsPolling] = useState(false); // Tracks background polling
  const [error, setError] = useState<string | null>(null); // Store error message string

  const fetchJob = useCallback(
    async (isPoll = false) => {
      if (!apiClient || !jobId) {
        setLoading(false); // Ensure initial loading stops if no ID/client
        // If no jobId is provided (e.g., create mode), don't fetch
        if (!jobId) setJob(null);
        return;
      }
      if (!isPoll) {
        setLoading(true); // Only set main loading for non-poll fetches
      }
      setIsPolling(isPoll); // Indicate if it's a poll
      setError(null);
      try {
        const response =
          await apiClient.getVerificationJobVerificationJobsVerificationJobIdGet(
            {
              verificationJobId: jobId,
            }
          );
        setJob(response.verificationJob || null);
      } catch (err) {
        console.error(`Failed to fetch verification job ${jobId}:`, err);
        setError(
          err instanceof Error ? err.message : "An unknown error occurred"
        );
      } finally {
        setLoading(false); // Stop initial loading indicator
        setIsPolling(false); // Stop polling indicator
      }
    },
    [apiClient, jobId]
  );

  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  // Add effect for polling
  useEffect(() => {
    if (!jobId) return; // Don't poll if there's no jobId

    const intervalId = setInterval(() => {
      // console.log(`Polling verification job ${jobId}...`); // Optional: for debugging
      fetchJob(true); // Pass true to indicate this is a poll
    }, 10000); // Poll every 10 seconds

    // Cleanup function to clear the interval
    return () => {
      // console.log(`Clearing interval for job ${jobId}`); // Optional: for debugging
      clearInterval(intervalId);
    };
  }, [jobId, fetchJob]); // Re-run if jobId or fetchJob changes

  // Expose both loading states if needed, but component primarily uses `loading` for initial spinner
  return { job, loading, isPolling, error, refetch: () => fetchJob(false) }; // Ensure manual refetch isn't marked as poll
};

/**
 * Hook to create a new verification job.
 *
 * @returns An object containing the create function, loading state, error state, and the created job data.
 */
export const useCreateVerificationJob = () => {
  const apiClient = useApiClient();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null); // Store error message string
  const [createdJob, setCreatedJob] = useState<VerificationJob | null>(null);

  const createJob = useCallback(
    async (jobData: CreateVerificationJobRequest) => {
      if (!apiClient) {
        setError("API client not available");
        return; // Return undefined or handle as needed
      }
      setLoading(true);
      setError(null);
      setCreatedJob(null);
      try {
        const response =
          await apiClient.createVerificationJobVerificationJobsPost({
            createVerificationJobRequest: jobData,
          });
        setCreatedJob(response.verificationJob);
        return response.verificationJob; // Return the created job
      } catch (err) {
        console.error("Failed to create verification job:", err);
        const apiError =
          err instanceof Error ? err : new Error("An unknown error occurred");
        setError(apiError.message);
        throw apiError; // Re-throw error to allow caller handling
      } finally {
        setLoading(false);
      }
    },
    [apiClient]
  );

  return { createJob, loading, error, createdJob };
};

/**
 * Hook to update an existing verification job.
 *
 * @returns An object containing the update function, loading state, error state, and the updated job data.
 */
export const useUpdateVerificationJob = () => {
  const apiClient = useApiClient();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null); // Store error message string
  const [updatedJob, setUpdatedJob] = useState<VerificationJob | null>(null);

  const updateJob = useCallback(
    async (jobId: string, jobData: UpdateVerificationJobRequest) => {
      if (!apiClient) {
        setError("API client not available");
        return; // Return undefined or handle as needed
      }
      setLoading(true);
      setError(null);
      setUpdatedJob(null);
      try {
        // Corrected method name to PUT and adjusted parameters
        const response =
          await apiClient.updateVerificationJobVerificationJobsVerificationJobIdPut(
            {
              verificationJobId: jobId, // Use verificationJobId based on typical patterns
              updateVerificationJobRequest: jobData,
            }
          );
        setUpdatedJob(response.verificationJob);
        return response.verificationJob; // Return the updated job
      } catch (err) {
        console.error("Failed to update verification job:", err);
        const apiError =
          err instanceof Error ? err : new Error("An unknown error occurred");
        setError(apiError.message);
        throw apiError; // Re-throw error to allow caller handling
      } finally {
        setLoading(false);
      }
    },
    [apiClient]
  );

  return { updateJob, loading, error, updatedJob };
};

/**
 * Hook to delete a verification job.
 *
 * @returns An object containing the delete function, loading state, error state, and a boolean indicating if deletion was successful.
 */
export const useDeleteVerificationJob = () => {
  const apiClient = useApiClient();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null); // Store error message string
  const [deleted, setDeleted] = useState(false);

  const deleteJob = useCallback(
    async (jobId: string) => {
      if (!apiClient) {
        setError("API client not available");
        return; // Return undefined or handle as needed
      }
      setLoading(true);
      setError(null);
      setDeleted(false);
      try {
        // Corrected method name and parameter key
        // Assuming the delete operation returns void or a simple confirmation
        await apiClient.deleteVerificationJobVerificationJobsVerificationJobIdDelete(
          {
            verificationJobId: jobId, // Use verificationJobId based on error and patterns
          }
        );
        setDeleted(true);
      } catch (err) {
        console.error("Failed to delete verification job:", err);
        const apiError =
          err instanceof Error ? err : new Error("An unknown error occurred");
        setError(apiError.message);
        throw apiError; // Re-throw error to allow caller handling
      } finally {
        setLoading(false);
      }
    },
    [apiClient]
  );

  return { deleteJob, loading, error, deleted };
};

/**
 * Hook to fetch logs for a specific verification job, with optional filtering.
 *
 * @param verificationJobId The ID of the verification job to fetch logs for. If undefined, no fetch occurs.
 * @param options Optional configuration object.
 * @param options.initialLimit The number of log entries to fetch initially and per page. Defaults to 20.
 * @param options.searchQuery An optional string to filter logs by message content.
 * @returns An object containing the logs, loading state, error state, a function to fetch the next page, and whether more logs are available.
 */
interface UseVerificationJobLogsOptions {
  initialLimit?: number;
  searchQuery?: string;
  logLevel?: string; // Add logLevel option
}

export const useVerificationJobLogs = (
  verificationJobId?: string,
  options: UseVerificationJobLogsOptions = {}
) => {
  const { initialLimit = 20, searchQuery, logLevel } = options; // Destructure options including logLevel
  const apiClient = useApiClient();
  const [logs, setLogs] = useState<VerificationJobLogEntry[]>([]);
  const [loading, setLoading] = useState(true); // For initial load
  const [loadingMore, setLoadingMore] = useState(false); // For subsequent loads
  const [error, setError] = useState<string | null>(null);
  const [lastEvaluatedKey, setLastEvaluatedKey] = useState<
    string | null | undefined
  >(undefined); // Store the key for the next page

  const fetchLogs = useCallback(
    async (key?: string | null) => {
      if (!apiClient || !verificationJobId) {
        setLoading(false);
        setLoadingMore(false);
        if (!verificationJobId) {
          setLogs([]);
          setLastEvaluatedKey(undefined);
        }
        return;
      }

      const isFetchingMore = !!key;
      if (isFetchingMore) {
        setLoadingMore(true);
      } else {
        setLoading(true); // Initial load
        setLogs([]); // Reset logs on initial fetch
      }
      setError(null);

      try {
        const response =
          await apiClient.getVerificationJobLogsVerificationJobsLogsVerificationJobIdGet(
            {
              verificationJobId: verificationJobId,
              limit: initialLimit,
              lastEvaluatedKey: key ?? undefined, // Pass the key if fetching more
              searchString: searchQuery || undefined, // Pass search query if provided
              logLevel: logLevel || undefined, // Pass log level if provided
            }
          );

        const newLogs =
          response.items.sort((a, b) => b.timestamp - a.timestamp) || [];
        setLogs((prevLogs) =>
          isFetchingMore ? [...prevLogs, ...newLogs] : newLogs
        );
        // Stringify the key before storing it in state
        setLastEvaluatedKey(
          response.lastEvaluatedKey
            ? JSON.stringify(response.lastEvaluatedKey)
            : undefined
        );
      } catch (err) {
        console.error(
          `Failed to fetch logs for verification job ${verificationJobId}:`,
          err
        );
        setError(
          err instanceof Error ? err.message : "An unknown error occurred"
        );
      } finally {
        setLoading(false); // Stop initial loading
        setLoadingMore(false); // Stop loading more indicator
      }
    },
    [apiClient, verificationJobId, initialLimit, searchQuery, logLevel] // Add logLevel to dependencies
  );

  // Initial fetch or refetch when verificationJobId, searchQuery, or logLevel changes
  useEffect(() => {
    // Reset state when dependencies change
    setLogs([]);
    setLastEvaluatedKey(undefined);
    setLoading(true);
    setError(null);
    fetchLogs(); // Fetch the first page
  }, [verificationJobId, searchQuery, logLevel, fetchLogs]); // Add logLevel to dependencies

  const fetchNextPage = useCallback(() => {
    if (lastEvaluatedKey) {
      fetchLogs(lastEvaluatedKey);
    }
  }, [fetchLogs, lastEvaluatedKey]);

  const hasMore = !!lastEvaluatedKey;

  return {
    logs,
    loading, // Initial loading state
    loadingMore, // Loading state for subsequent pages
    error,
    fetchNextPage,
    hasMore, // Boolean indicating if more logs can be fetched
    refetch: () => fetchLogs(), // Refetch the first page
  };
};

/**
 * Hook to trigger the start of a verification job's execution.
 *
 * @returns An object containing the start function, loading state, and error state.
 */
export const useStartVerificationJobExecution = () => {
  const apiClient = useApiClient();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startExecution = useCallback(
    async (jobId: string) => {
      if (!apiClient) {
        setError("API client not available");
        return; // Or throw error
      }
      setLoading(true);
      setError(null);
      try {
        // Assuming the generated client method follows this pattern:
        // operationId: start_verification_job_execution_verification_jobs__verification_job_id__start_post
        // becomes: startVerificationJobExecutionVerificationJobsVerificationJobIdStartPost
        await apiClient.startVerificationJobExecutionVerificationJobsVerificationJobIdStartPost(
          {
            verificationJobId: jobId,
          }
        );
        // Optionally return something or just resolve on success
      } catch (err) {
        console.error(`Failed to start execution for job ${jobId}:`, err);
        const apiError =
          err instanceof Error ? err : new Error("An unknown error occurred");
        setError(apiError.message);
        throw apiError; // Re-throw error to allow caller handling
      } finally {
        setLoading(false);
      }
    },
    [apiClient]
  );

  return { startExecution, loading, error };
};
