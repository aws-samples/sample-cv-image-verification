import React, { useState, useEffect, useMemo } from "react"; // Removed useCallback
import { useNavigate } from "react-router-dom";

import {
  Container,
  Header,
  SpaceBetween,
  FormField,
  Input,
  Button,
  Form,
  Alert,
  Spinner,
  Select,
  StatusIndicator,
  Link,
  Box,
  Table,
  Modal,
  TableProps,
  Tabs,
  // KeyValuePairs, // Keep Tabs import // Removed unused import
  SelectProps,
  Checkbox, // Import SelectProps for options type
} from "@cloudscape-design/components";
import { useApiClient } from "../ApiClient"; // Import API client hook
import {
  useVerificationJob,
  useCreateVerificationJob,
  useVerificationJobLogs,
  useStartVerificationJobExecution, // Import the start execution hook
} from "../../hooks/VerificationJobs";
import { useGetAllCollections } from "../../hooks/Collections";
import { useGetAgentsByVerificationJob } from "../../hooks/Agents";
import {
  // VerificationJob, // Removed unused import
  CreateVerificationJobRequest,
  // UpdateVerificationJobRequest, // Removed unused import
  AssessmentStatus,
  VerificationJobLogEntry, // Add Log Entry type import
  Agent,
} from "@aws-samples/cv-verification-api-client/src";
import {
  CollectionFileInstance,
  ItemInstance,
} from "@aws-samples/cv-verification-api-client/src";
import { useAppLayoutContext } from "../../App";

interface VerificationJobDetailsProps {
  jobId?: string;
}

// --- Component Definition --- (Moved helper functions inside)
export const VerificationJobDetails: React.FC<VerificationJobDetailsProps> = ({
  jobId,
}) => {
  const appLayout = useAppLayoutContext();

  const navigate = useNavigate();
  const apiClient = useApiClient(); // Get API client instance
  const isCreating = !jobId;
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalImageUrl, setModalImageUrl] = useState<string | null>(null);
  const [isReasoningModalOpen, setIsReasoningModalOpen] = useState(false); // State for reasoning modal visibility
  const [reasoningModalContent, setReasoningModalContent] = useState<
    string | null
  >(null); // State for reasoning modal content
  const [reasoningModalTitle, setReasoningModalTitle] = useState<string | null>(
    null
  );
  const [fileUrls, setFileUrls] = useState<Record<string, string>>({}); // State for presigned URLs { fileId: url }
  const [loadingUrls, setLoadingUrls] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);

  const [activeTabId, setActiveTabId] = useState("details"); // State for active tab
  const [logSearchQuery, setLogSearchQuery] = useState(""); // State for log search query
  const [debouncedLogSearchQuery, setDebouncedLogSearchQuery] = useState(""); // State for debounced query
  const [selectedLogLevel, setSelectedLogLevel] =
    useState<SelectProps.Option | null>(
      { label: "ALL", value: "ALL" } // Default to ALL
    ); // State for selected log level filter

  // --- Hooks ---
  const {
    job: fetchedJob,
    loading: loadingJob,
    error: fetchError,
    refetch,
  } = useVerificationJob(jobId);
  const {
    createJob,
    loading: creatingJob,
    error: createError,
  } = useCreateVerificationJob();
  const {
    data: collections,
    isLoading: loadingCollections,
    error: workOrdersError,
  } = useGetAllCollections();
  const {
    logs,
    loading: loadingLogs, // Initial load state
    loadingMore: loadingMoreLogs, // Loading state for next page
    error: logsError,
    fetchNextPage: fetchNextLogsPage,
    hasMore: hasMoreLogs,
    refetch: refetchLogs,
  } = useVerificationJobLogs(jobId, {
    searchQuery: debouncedLogSearchQuery,
    logLevel:
      selectedLogLevel?.value === "ALL" ? undefined : selectedLogLevel?.value, // Pass selected log level, undefined if 'ALL'
  });

  const {
    startExecution,
    loading: startingExecution, // Use hook's loading state
    error: startExecutionError, // Use hook's error state
  } = useStartVerificationJobExecution(); // Use the start execution hook

  const {
    data: agents,
    isLoading: loadingAgents,
    error: agentsError,
  } = useGetAgentsByVerificationJob(jobId || "");

  // --- Form State ---
  const [collectionId, setCollectionId] = useState("");
  const [searchInternet, setSearchInternet] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [noCollectionsError, setNoCollectionsError] = useState<string | null>(
    null
  );

  useEffect(() => {
    appLayout.setAppLayoutProps({
      breadcrumbs: (
        <>
          <Box display="inline">
            / <Link href="/verificationjobs">Verification Jobs</Link> / Edit Job{" "}
            {isCreating || !fetchedJob ? "" : fetchedJob.id}
          </Box>
        </>
      ),
    });
  }, [fetchedJob, isCreating, appLayout]);

  // Populate form when job data is loaded or reset when creating/error
  useEffect(() => {
    if (fetchedJob && !isCreating) {
      setCollectionId(fetchedJob.collectionId || "");
    }
    if (isCreating || fetchError) {
      setCollectionId("");
    }
  }, [fetchedJob, isCreating, fetchError]);

  useEffect(() => {
    // Ensure we have the workOrderId from the fetchedJob
    if (fetchedJob?.collectionId && apiClient) {
      const fetchUrls = async () => {
        setLoadingUrls(true);
        setUrlError(null);
        try {
          const response =
            await apiClient.getVerificationJobFilesUrlVerificationJobsVerificationJobIdFilesPresignedUrlsGet(
              {
                verificationJobId: fetchedJob.id,
              }
            );
          const urls = response.presignedUrls || {};
          setFileUrls(urls);
          console.log("Fetched fileUrls state:", JSON.stringify(urls));
        } catch (error) {
          console.error(
            "Failed to fetch presigned URLs for collection:",
            error
          );
          setUrlError(
            error instanceof Error
              ? error.message
              : "Failed to load file previews."
          );
          setFileUrls({}); // Clear URLs on error
        } finally {
          setLoadingUrls(false);
        }
      };
      fetchUrls();
    } else {
      // Clear URLs if workOrderId or apiClient is missing
      setFileUrls({});
    }
  }, [fetchedJob?.collectionId, apiClient]); // Dependencies updated to workOrderId

  useEffect(() => {
    if (
      isCreating &&
      !loadingCollections &&
      collections &&
      collections.length === 0
    ) {
      setNoCollectionsError(
        "No collections available. Please create a collections first."
      );
    } else {
      setNoCollectionsError(null);
    }
  }, [isCreating, loadingCollections, collections]);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedLogSearchQuery(logSearchQuery);
    }, 500); // 500ms debounce delay

    return () => {
      clearTimeout(handler);
    };
  }, [logSearchQuery]);

  // --- Helper Functions ---
  const formatFileSize = (bytes?: number | null): string => {
    if (bytes === null || bytes === undefined || isNaN(bytes) || bytes < 0) {
      return "-";
    }
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const isImage = (contentType?: string | null): boolean => {
    return !!contentType && contentType.startsWith("image/");
  };

  const handleThumbnailClick = (imageUrl: string) => {
    setModalImageUrl(imageUrl);
    setIsModalOpen(true);
  };

  // Removed unused renderFileStatus function

  const renderStatus = (status?: AssessmentStatus) => {
    if (!status) return <StatusIndicator type="pending">-</StatusIndicator>;
    switch (status) {
      case AssessmentStatus.Pending:
        return <StatusIndicator type="pending">Pending</StatusIndicator>;
      case AssessmentStatus.Assessing:
        return <StatusIndicator type="in-progress">Assessing</StatusIndicator>;
      case AssessmentStatus.Approved:
        return <StatusIndicator type="success">Approved</StatusIndicator>;
      case AssessmentStatus.Rejected:
        return <StatusIndicator type="error">Rejected</StatusIndicator>;
      case AssessmentStatus.NeedsReview:
        return <StatusIndicator type="info">Needs Review</StatusIndicator>;
      default:
        return <StatusIndicator type="pending">{status}</StatusIndicator>;
    }
  };

  const handleStartExecution = async () => {
    if (!jobId) return;
    // Clear previous success/error messages if needed
    console.log("Start execution clicked for job:", jobId);
    try {
      await startExecution(jobId);
      // Optionally show success message or refetch
      refetch(); // Refetch job details to update status
    } catch (err) {
      // Error is captured by the hook's startExecutionError state
      console.error("Start execution failed in component:", err);
    }
  };

  // --- Event Handlers ---
  const handleCancel = () => {
    navigate("/verificationjobs");
  };

  const validateForm = (): boolean => {
    if (!collectionId.trim()) {
      setFormError("Collection ID is required.");
      return false;
    }
    setFormError(null);
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    const jobData: CreateVerificationJobRequest = {
      collectionId,
      searchInternet,
    };

    try {
      if (isCreating) {
        const result = await createJob(jobData);
        if (result?.id) navigate(`/job/${result.id}`);
      } else if (jobId) {
        refetch();
      }
    } catch (err) {
      console.error("Form submission error:", err);
    }
  };

  // --- Table Column Definitions ---
  const fileTableColumnDefinitions: ReadonlyArray<
    TableProps.ColumnDefinition<CollectionFileInstance>
  > = useMemo(
    () => [
      {
        id: "thumbnail",
        header: "Preview",
        cell: (item) => {
          const imageUrl = fileUrls[item.id]; // Use file ID as key
          // DEBUG: Log item ID and looked-up URL
          console.log(`File ID: ${item.id}, Looked up URL: ${imageUrl}`);
          return isImage(item.contentType) && imageUrl ? (
            <div
              style={{
                width: "50px",
                height: "50px",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
              }}
            >
              <img
                src={imageUrl}
                alt={`Thumbnail for ${item.filename}`}
                style={{
                  maxWidth: "100%",
                  maxHeight: "100%",
                  objectFit: "contain",
                  cursor: "pointer",
                }}
                onClick={() => handleThumbnailClick(imageUrl)}
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }} // Hide broken image
              />
            </div>
          ) : (
            "-" // Display a dash when no image preview is available
          );
        },
        minWidth: 150,
      },
      {
        id: "filename",
        header: "Filename",
        cell: (item) => item.filename,
        sortingField: "filename",
        minWidth: 200,
      },
      {
        id: "contentType",
        header: "Content Type",
        cell: (item) => item.contentType || "-",
        minWidth: 150,
      },
      {
        id: "size",
        header: "Size",
        cell: (item) => formatFileSize(item.size),
        sortingField: "size",
        minWidth: 100,
      },
      {
        id: "description",
        header: "Description",
        cell: (item) => item.description || "-",
        minWidth: 200,
      },

      // eslint-disable-next-line react-hooks/exhaustive-deps
    ],
    [fileUrls]
  ); // Dependency: fileUrls

  // --- Log Table Column Definitions ---
  const logTableColumnDefinitions: ReadonlyArray<
    TableProps.ColumnDefinition<VerificationJobLogEntry>
  > = useMemo(
    () => [
      {
        id: "timestamp",
        header: "Timestamp",
        cell: (item) =>
          item.timestamp
            ? new Date(item.timestamp * 1000).toLocaleString()
            : "-",
        sortingField: "timestamp",
        minWidth: 180,
      },
      {
        id: "level",
        header: "Level",
        cell: (item) => item.level || "-",
        minWidth: 100,
      },
      {
        id: "message", // Changed from 'message' to 'description'
        header: "Message", // Changed header
        cell: (item) => item.message || "-", // Use the correct property
        minWidth: 400,
      },
      // Removed columns for 'level' and 'details' as they don't exist on the type
    ],
    []
  );

  // Log Level Options
  const logLevelOptions: SelectProps.Option[] = [
    { label: "ALL", value: "ALL" },
    { label: "INFO", value: "INFO" },
    { label: "ERROR", value: "ERROR" },
    { label: "DEBUG", value: "DEBUG" },
    { label: "CRITICAL", value: "CRITICAL" },
  ];

  // --- Agent Table Column Definitions ---
  const agentTableColumnDefinitions: ReadonlyArray<
    TableProps.ColumnDefinition<Agent>
  > = useMemo(
    () => [
      {
        id: "name",
        header: "Name",
        cell: (item) => (
          <Link target="_blank" href={`/agent/${item.id}`}>
            {item.name}
          </Link>
        ),
        sortingField: "name",
        minWidth: 200,
      },
      {
        id: "type",
        header: "Type",
        cell: (item) => item.type || "-",
        minWidth: 150,
      },
      {
        id: "description",
        header: "Description",
        cell: (item) => item.description || "-",
        minWidth: 250,
      },
      {
        id: "apiEndpoint",
        header: "API Endpoint",
        cell: (item) => item.apiEndpoint || "-",
        minWidth: 200,
      },
      {
        id: "knowledgeBaseId",
        header: "Knowledge Base ID",
        cell: (item) => item.knowledgeBaseId || "-",
        minWidth: 180,
      },
      {
        id: "createdAt",
        header: "Created At",
        cell: (item) =>
          item.createdAt
            ? new Date(item.createdAt * 1000).toLocaleString()
            : "-",
        sortingField: "createdAt",
        minWidth: 180,
      },
    ],
    []
  );

  // --- Loading and Error States ---
  // Adjusted main loading state to exclude log loading
  const loading =
    loadingJob ||
    creatingJob ||
    // updatingJob || // Removed from loading state
    (isCreating && loadingCollections) ||
    loadingUrls || // Include loadingUrls
    startingExecution; // Add start execution loading state
  const apiError =
    (isCreating && workOrdersError) ||
    fetchError ||
    createError ||
    // updateError || // Removed from error state
    urlError ||
    logsError || // Add logs error state
    startExecutionError || // Add start execution error state
    agentsError; // Add agents error state
  const apiErrorMessage = [
    isCreating ? workOrdersError : null, // Directly use the string error or null
    fetchError, // Directly use the string error or null
    createError, // Directly use the string error or null
    urlError, // Already a string or null
    logsError, // Add logs error message
    startExecutionError, // Add start execution error message
    agentsError, // Add agents error message
  ]
    .filter(Boolean) // Remove null/undefined entries
    .join("; "); // Join multiple errors

  // --- Render ---
  return (
    <Form
      actions={
        <SpaceBetween direction="horizontal" size="m">
          <Button variant="link" onClick={handleCancel} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            loading={loading} // Use the adjusted loading state
            disabled={
              loading || // Use the adjusted loading state
              !isCreating ||
              (isCreating && (!collections || collections.length === 0))
            }
          >
            {isCreating ? "Create Verification Job" : "Save Changes"}
          </Button>
        </SpaceBetween>
      }
      header={
        <Header variant="h1">
          {isCreating
            ? "Create Verification Job"
            : `Verification Job: ${jobId}`}
        </Header>
      }
      errorText={formError || apiErrorMessage || noCollectionsError}
    >
      {loading && !apiError ? ( // Use the adjusted loading state
        <Spinner size="large" />
      ) : fetchError && !isCreating ? (
        <Alert statusIconAriaLabel="Error" type="error">
          {noCollectionsError || `Failed to load data: ${apiErrorMessage}.`}{" "}
          {fetchError && !isCreating && (
            <Button onClick={refetch}>Retry</Button>
          )}
        </Alert>
      ) : noCollectionsError ? (
        <Alert statusIconAriaLabel="Error" type="error">
          {noCollectionsError}
        </Alert>
      ) : (
        <Container>
          <SpaceBetween direction="vertical" size="l">
            {/* Collection Selection or Display */}
            {isCreating ? (
              <SpaceBetween direction="vertical" size="l">
                <FormField
                  label="Collection"
                  errorText={
                    (formError && !collectionId.trim()
                      ? formError
                      : undefined) ||
                    (isCreating && workOrdersError
                      ? apiErrorMessage
                      : undefined)
                  }
                  description="Select the collection to associate with this verification job."
                >
                  <Select
                    selectedOption={
                      collections?.find((wo) => wo.id === collectionId)
                        ? {
                            label: `${
                              collections?.find((wo) => wo.id === collectionId)
                                ?.description
                            } - ${collectionId}`,
                            value: collectionId,
                          }
                        : null
                    }
                    onChange={({ detail }) =>
                      setCollectionId(detail.selectedOption.value || "")
                    }
                    options={
                      collections?.map((wo) => ({
                        label: `${wo.description?.substring(0, 20)}... - ${
                          wo.id
                        }`, // Added ellipsis
                        value: wo.id,
                      })) || []
                    }
                    loadingText="Loading collections..."
                    placeholder="Choose a collection"
                    statusType={
                      isCreating && loadingCollections
                        ? "loading"
                        : isCreating && workOrdersError
                        ? "error"
                        : "finished"
                    }
                    disabled={loading} // Only disable based on general loading state
                    empty="No collections found"
                    errorText={
                      isCreating && workOrdersError
                        ? `Failed to load collections: ${apiErrorMessage}`
                        : undefined
                    }
                    filteringType="auto" // Enable searching
                  />
                </FormField>
                <FormField description="If checked, the verification job will search for Internet resources to augment its findings.">
                  <Checkbox
                    onChange={(e) => setSearchInternet(e.detail.checked)}
                    checked={searchInternet}
                  >
                    Use Internet Search to augment findings
                  </Checkbox>
                </FormField>
              </SpaceBetween>
            ) : (
              fetchedJob && (
                <SpaceBetween
                  direction="horizontal"
                  size="s"
                  alignItems="center"
                >
                  <Header variant="h3">Collection:</Header>
                  <Box fontSize="heading-s">
                    <Link
                      target="_blank"
                      href={"/collection/" + fetchedJob.collectionId}
                    >
                      {fetchedJob.collectionName}
                    </Link>
                  </Box>
                </SpaceBetween>
              )
            )}

            {/* Display Fields (Read-only for existing jobs) */}
            {!isCreating && fetchedJob && (
              <>
                {/* Tabs for Details, Items, and Files */}
                <Tabs
                  key={fetchedJob.id} // Add key prop
                  activeTabId={activeTabId} // Control active tab
                  onChange={({ detail }) => setActiveTabId(detail.activeTabId)} // Update state on change
                  tabs={[
                    {
                      label: "Details",
                      id: "details",
                      content: (
                        <SpaceBetween direction="vertical" size="l">
                          <FormField label="Job ID">
                            <Box>{fetchedJob.id}</Box>
                          </FormField>
                          <FormField label="Collection">
                            <Box>{fetchedJob.collectionName}</Box>
                          </FormField>
                          <FormField label="Status">
                            <SpaceBetween direction="horizontal" size="s">
                              {renderStatus(fetchedJob.status)}
                              {/* Add Start Execution Button Here */}
                              {fetchedJob.status ===
                                AssessmentStatus.Pending && ( // Only show if Pending
                                <Button
                                  variant="normal"
                                  onClick={handleStartExecution}
                                  loading={startingExecution}
                                  disabled={startingExecution || loadingJob} // Disable if busy
                                >
                                  Start Execution
                                </Button>
                              )}
                            </SpaceBetween>
                          </FormField>
                          {/* Conditionally display error message */}
                          {startExecutionError && ( // Display start execution error
                            <Alert
                              statusIconAriaLabel="Error"
                              type="error"
                              header="Failed to start execution"
                            >
                              {startExecutionError}
                            </Alert>
                          )}
                          {fetchedJob.status === AssessmentStatus.Error && // Corrected enum case
                            fetchedJob.errorMessage && ( // Corrected property name
                              <Alert
                                statusIconAriaLabel="Error"
                                type="error"
                                header="Job Error"
                              >
                                {fetchedJob.errorMessage}{" "}
                                {/* Corrected property name */}
                              </Alert>
                            )}
                          <FormField label="Confidence Score">
                            <Box>
                              {fetchedJob.confidence
                                ? (fetchedJob.confidence * 100).toString() + "%"
                                : "-"}
                            </Box>
                          </FormField>
                          <FormField label="Analysis Cost">
                            <Box>{`$${(fetchedJob.totalCost ?? 0).toFixed(
                              6
                            )}`}</Box>
                          </FormField>
                          <FormField label="Search Internet">
                            <Box>
                              {fetchedJob.searchInternet ? "Yes" : "No"}
                            </Box>
                          </FormField>
                          <FormField label="Created At">
                            <Box>
                              {fetchedJob.createdAt
                                ? new Date(
                                    fetchedJob.createdAt * 1000
                                  ).toLocaleString()
                                : "-"}
                            </Box>
                          </FormField>
                          <FormField label="Last Updated At">
                            <Box>
                              {fetchedJob.updatedAt
                                ? new Date(
                                    fetchedJob.updatedAt * 1000
                                  ).toLocaleString()
                                : "-"}
                            </Box>
                          </FormField>

                          {/* Aggregated Results */}
                          {fetchedJob.aggregatedResults && (
                            <FormField label="Aggregated Results">
                              <Box
                                variant="div"
                                padding="s"
                                // Removed className="markdown-content" as ReactMarkdown is removed
                              >
                                <pre
                                  style={{
                                    whiteSpace: "pre-wrap",
                                    wordWrap: "break-word",
                                  }}
                                >
                                  {fetchedJob.aggregatedResults}
                                </pre>
                              </Box>
                            </FormField>
                          )}
                        </SpaceBetween>
                      ),
                    },
                    {
                      label: "Items",
                      id: "sor-instances",
                      content: (
                        <Table
                          columnDefinitions={[
                            {
                              id: "name",
                              header: "Item Name",
                              cell: (item: ItemInstance) => (
                                <Link
                                  target="_blank"
                                  href={`/itemdetail/${item.itemId}`}
                                >
                                  {item.name}
                                </Link>
                              ),
                              sortingField: "name",
                            },
                            {
                              id: "description",
                              header: "Description",
                              cell: (item: ItemInstance) => item.description,
                            },
                            {
                              id: "mandatory",
                              header: "Mandatory",
                              cell: (item: ItemInstance) =>
                                item.descriptionFilteringRulesApplied.find(
                                  (a) => a.mandatory
                                )
                                  ? "Yes"
                                  : "No",
                            },
                            {
                              id: "status",
                              header: "Status",
                              cell: (item: ItemInstance) =>
                                renderStatus(item.status),
                            },
                            {
                              id: "cluster",
                              header: "Cluster",
                              cell: (item: ItemInstance) =>
                                item.clusterNumber || "-",
                            },
                            {
                              id: "confidence",
                              header: "Confidence",
                              cell: (item: ItemInstance) =>
                                item.confidence
                                  ? (item.confidence * 100)
                                      ?.toFixed(2)
                                      .toString() + "%"
                                  : "-",
                            },
                            {
                              id: "reasoning",
                              maxWidth: 200,
                              header: "Reasoning",
                              cell: (item: ItemInstance) => {
                                const reasoning = item.assessmentReasoning;
                                if (reasoning) {
                                  const displayReasoning =
                                    reasoning.length > 20
                                      ? reasoning.substring(0, 20) + "..."
                                      : reasoning;
                                  return (
                                    <Link
                                      onFollow={(e) => {
                                        e.preventDefault(); // Prevent default link behavior
                                        setReasoningModalTitle(
                                          item.description
                                        );
                                        setReasoningModalContent(reasoning);
                                        setIsReasoningModalOpen(true);
                                      }}
                                      href="#"
                                    >
                                      {displayReasoning}
                                    </Link>
                                  );
                                }
                                return "-";
                              },
                            },
                            {
                              id: "approved_files",
                              header: "Approved Files",
                              cell: (item: ItemInstance) => {
                                return (
                                  <div
                                    style={{
                                      // width: '50px',
                                      // height: '50px',
                                      maxWidth: "400px",
                                      display: "flex",
                                      justifyContent: "left",
                                      alignItems: "center",
                                      flexWrap: "wrap",
                                      gap: "12px",
                                    }}
                                  >
                                    {item.approvedFiles?.map((file) => {
                                      const imageUrl = fileUrls[file.id]; // Use file ID as key
                                      console.log(
                                        `File ID: ${file.id}, Looked up URL: ${imageUrl}`
                                      );
                                      return isImage(file.contentType) &&
                                        imageUrl ? (
                                        <div
                                          style={{
                                            width: "50px",
                                            height: "50px",
                                            display: "flex",
                                            justifyContent: "center",
                                            alignItems: "center",
                                          }}
                                        >
                                          <img
                                            src={imageUrl}
                                            alt={`Thumbnail for ${file.filename}`}
                                            style={{
                                              maxWidth: "100%",
                                              maxHeight: "100%",
                                              objectFit: "contain",
                                              cursor: "pointer",
                                            }}
                                            onClick={() =>
                                              handleThumbnailClick(imageUrl)
                                            }
                                            onError={(e) => {
                                              e.currentTarget.style.display =
                                                "none";
                                            }} // Hide broken image
                                          />
                                        </div>
                                      ) : (
                                        "-" // Display a dash when no image preview is available
                                      );
                                    })}
                                  </div>
                                );
                              },
                            },
                          ]}
                          items={fetchedJob.items || []}
                          loadingText="Associated Items"
                          empty={
                            <Box textAlign="center" color="inherit">
                              <b>No item instances found for this job.</b>
                            </Box>
                          }
                          header={
                            <Header
                              counter={`(${(fetchedJob.items || []).length})`}
                            >
                              Item Verification
                            </Header>
                          }
                          variant="embedded"
                        />
                      ),
                    },
                    {
                      label: "Associated Files",
                      id: "associated-files",
                      content: (
                        <>
                          {urlError && (
                            <Alert
                              statusIconAriaLabel="Error"
                              type="error"
                              header="Error loading file previews"
                            >
                              {urlError}
                            </Alert>
                          )}
                          <Table
                            columnDefinitions={fileTableColumnDefinitions}
                            items={fetchedJob.files || []}
                            loading={loadingUrls}
                            loadingText="Loading associated files"
                            empty={
                              <Box textAlign="center" color="inherit">
                                <b>No files found for this job.</b>
                              </Box>
                            }
                            header={
                              <Header
                                counter={`(${(fetchedJob.files || []).length})`}
                              >
                                Associated Files
                              </Header>
                            }
                            variant="embedded"
                          />
                        </>
                      ),
                    },
                    {
                      label: "Agents",
                      id: "agents",
                      content: (
                        <>
                          {agentsError && (
                            <Alert
                              statusIconAriaLabel="Error"
                              type="error"
                              header="Error loading agents"
                            >
                              {typeof agentsError === "string"
                                ? agentsError
                                : "Failed to load agents"}
                            </Alert>
                          )}
                          <Table
                            columnDefinitions={agentTableColumnDefinitions}
                            items={agents || []}
                            loading={loadingAgents}
                            loadingText="Loading agents"
                            empty={
                              <Box textAlign="center" color="inherit">
                                <b>No agents found for this job.</b>
                              </Box>
                            }
                            header={
                              <Header counter={`(${(agents || []).length})`}>
                                Agents Used in Job
                              </Header>
                            }
                            variant="embedded"
                          />
                        </>
                      ),
                    },
                    {
                      label: "Logs",
                      id: "logging",
                      content: (
                        <>
                          {logsError && (
                            <Alert
                              statusIconAriaLabel="Error"
                              type="error"
                              header="Error loading logs"
                            >
                              {logsError}{" "}
                              <Button onClick={refetchLogs}>Retry</Button>
                            </Alert>
                          )}
                          <Table
                            stripedRows
                            columnDefinitions={logTableColumnDefinitions}
                            items={logs}
                            loading={loadingLogs} // Use initial loading state here for the table itself
                            loadingText="Loading logs"
                            empty={
                              <Box textAlign="center" color="inherit">
                                <b>No logs found for this job.</b>
                                {debouncedLogSearchQuery && (
                                  <p>Try refining your search.</p>
                                )}
                              </Box>
                            }
                            header={
                              <Header
                                counter={`(${logs.length})`}
                                actions={
                                  <SpaceBetween
                                    direction="horizontal"
                                    size="xs"
                                  >
                                    {/* Log Level Filter Dropdown */}
                                    <Select
                                      selectedOption={selectedLogLevel}
                                      onChange={({ detail }) =>
                                        setSelectedLogLevel(
                                          detail.selectedOption
                                        )
                                      }
                                      options={logLevelOptions}
                                      placeholder="Filter by level"
                                      ariaLabel="Filter logs by level"
                                      disabled={loadingLogs || loadingMoreLogs}
                                    />
                                    {/* Log Search Input */}
                                    <Input
                                      type="search"
                                      value={logSearchQuery}
                                      onChange={({ detail }) =>
                                        setLogSearchQuery(detail.value)
                                      }
                                      placeholder="Search logs..."
                                      ariaLabel="Search logs"
                                      disabled={loadingLogs || loadingMoreLogs}
                                    />
                                    <Button
                                      iconName="refresh"
                                      variant="icon"
                                      onClick={(event) => {
                                        // Corrected onClick handler
                                        event.preventDefault(); // Prevent default form submission
                                        event.stopPropagation(); // Prevent event bubbling
                                        // Refetch with current search query
                                        refetchLogs();
                                      }}
                                      disabled={loadingLogs || loadingMoreLogs} // Keep button disabled while logs are loading/reloading
                                      ariaLabel="Refresh logs"
                                    />
                                  </SpaceBetween>
                                }
                              >
                                Job Logs
                              </Header>
                            }
                            variant="embedded"
                            footer={
                              hasMoreLogs ? (
                                <Box textAlign="center" padding={{ top: "m" }}>
                                  <Button
                                    onClick={fetchNextLogsPage}
                                    loading={loadingMoreLogs}
                                    disabled={loadingMoreLogs}
                                  >
                                    Load More Logs
                                  </Button>
                                </Box>
                              ) : null
                            }
                          />
                        </>
                      ),
                    },
                  ]}
                ></Tabs>
              </>
            )}
          </SpaceBetween>
        </Container>
      )}

      {/* Image Modal */}
      <Modal
        onDismiss={() => setIsModalOpen(false)}
        visible={isModalOpen}
        closeAriaLabel="Close modal"
        size="large"
        header="Image Preview"
      >
        {modalImageUrl && (
          <img // Use standard img tag
            src={modalImageUrl}
            alt="Full size preview"
            style={{
              maxWidth: "100%",
              maxHeight: "70vh",
              objectFit: "contain",
            }}
          />
        )}
      </Modal>

      {/* Reasoning Modal */}
      <Modal
        onDismiss={() => setIsReasoningModalOpen(false)}
        visible={isReasoningModalOpen}
        closeAriaLabel="Close reasoning modal"
        size="large"
        header={reasoningModalTitle}
      >
        {reasoningModalContent && (
          <Box variant="div" padding="s">
            {reasoningModalContent}
          </Box>
        )}
      </Modal>
    </Form>
  );
};
