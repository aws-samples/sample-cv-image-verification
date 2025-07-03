import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom"; // Import useNavigate
import {
  Table,
  Box,
  Header,
  Pagination,
  TextFilter,
  Button,
  ContentLayout,
  Link,
  SpaceBetween,
  Alert,
  Modal, // Added for confirmation dialog
  StatusIndicator, // Added for status rendering
} from "@cloudscape-design/components";
import {
  AssessmentStatus,
  VerificationJobDto, // Added for status enum
} from "@aws-samples/cv-verification-api-client/src";
import { useAppLayoutContext } from "../../App";
import {
  useVerificationJobs,
  useDeleteVerificationJob, // Import the delete hook
  useStartVerificationJobExecution, // Import the start execution hook
} from "../../hooks/VerificationJobs";

export const VerificationJobsListPage: React.FC = () => {
  const navigate = useNavigate(); // Add useNavigate
  const {
    jobs,
    loading: loadingJobs,
    error: jobsError,
    refetch,
  } = useVerificationJobs(); // Use the hook, rename loading/error
  const {
    deleteJob,
    loading: deletingJob,
    error: deleteError,
  } = useDeleteVerificationJob(); // Use the delete hook
  const {
    startExecution,
    loading: startingExecution,
    error: startExecutionError,
  } = useStartVerificationJobExecution(); // Use the start execution hook
  const [selectedItems, setSelectedItems] = useState<VerificationJobDto[]>([]);
  const [filteringText, setFilteringText] = useState("");
  const [isDeleteModalVisible, setIsDeleteModalVisible] = useState(false); // State for modal visibility
  const [jobToDeleteId, setJobToDeleteId] = useState<string | null>(null); // State for job ID to delete
  const appLayout = useAppLayoutContext();

  useEffect(() => {
    appLayout.setAppLayoutProps({
      breadcrumbs: (
        <>
          <Box display="inline">/ Verification Jobs</Box>
        </>
      ),
    });
  }, []);

  // Filtering logic remains in the component
  const filteredJobs = jobs.filter(
    (job) =>
      // Basic filtering example, adjust as needed
      job.id?.toLowerCase().includes(filteringText.toLowerCase()) ||
      job.status?.toLowerCase().includes(filteringText.toLowerCase()) ||
      job.collectionId?.toLowerCase().includes(filteringText.toLowerCase()) // Corrected property name
  );

  const handleCreateClick = () => {
    navigate("/newjob"); // Navigate to the create page
  };

  // Renamed from handleDeleteClick to handle row action, now repurposed for header button
  const handleDeleteSelectedClick = () => {
    if (selectedItems.length !== 1 || !selectedItems[0].id) return; // Ensure exactly one item is selected and has an ID
    setJobToDeleteId(selectedItems[0].id);
    setIsDeleteModalVisible(true);
  };

  const handleStartExecutionClick = async () => {
    if (selectedItems.length !== 1 || !selectedItems[0].id) return;
    const jobId = selectedItems[0].id;
    try {
      await startExecution(jobId);
      // Optionally show a success flash message here
      // Maybe refetch the job list if the status changes?
      refetch(); // Refetch to update status
    } catch (err) {
      // Error is captured in startExecutionError state by the hook
      console.error("Start execution failed in component:", err);
    }
  };

  const handleConfirmDelete = async () => {
    if (!jobToDeleteId) return;
    // Error state is handled by the useDeleteVerificationJob hook
    try {
      await deleteJob(jobToDeleteId);
      // If deleteJob throws, the catch block below handles it.
      // If it succeeds, the hook's error state should be null.
      refetch(); // Refresh the list after successful deletion
      setIsDeleteModalVisible(false);
      setJobToDeleteId(null);
      // Optionally show a success flash message here
    } catch (err) {
      // The hook already captures the error in `deleteError`.
      // We might still want to log it or handle UI specifics here.
      console.error("Delete operation failed in component:", err);
      // Keep the modal open so the user sees the error message below it,
      // or close it if the Alert outside the modal is preferred.
      // setIsDeleteModalVisible(false);
    }
  };

  const handleCancelDelete = () => {
    setIsDeleteModalVisible(false);
    setJobToDeleteId(null);
  };

  // Helper function to render status with appropriate indicator
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
        return <StatusIndicator type="warning">Rejected</StatusIndicator>;
      case AssessmentStatus.NeedsReview:
        return <StatusIndicator type="info">Needs Review</StatusIndicator>;
      default: {
        // Handle potential string values if the enum isn't strictly enforced
        const lowerStatus = String(status).toLowerCase();
        if (lowerStatus === "pending")
          return <StatusIndicator type="pending">Pending</StatusIndicator>;
        if (lowerStatus === "assessing")
          return (
            <StatusIndicator type="in-progress">Assessing</StatusIndicator>
          );
        if (lowerStatus === "approved")
          return <StatusIndicator type="success">Approved</StatusIndicator>;
        if (lowerStatus === "rejected")
          return <StatusIndicator type="warning">Rejected</StatusIndicator>;
        if (lowerStatus === "needs_review")
          return <StatusIndicator type="info">Needs Review</StatusIndicator>;
        if (lowerStatus === "error")
          return <StatusIndicator type="error">Error</StatusIndicator>;
        // Fallback for unknown statuses
        return <StatusIndicator type="pending">{status}</StatusIndicator>;
      }
    }
  };

  return (
    <ContentLayout
      header={
        <SpaceBetween size="m">
          <Header
            variant="h1"
            description="View and manage verification jobs."
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="icon"
                  iconName="refresh"
                  ariaLabel="Refresh jobs"
                  onClick={refetch}
                  disabled={loadingJobs}
                />
                <Button
                  variant="normal" // Changed variant for distinction or keep as primary if preferred
                  onClick={handleDeleteSelectedClick}
                  disabled={
                    selectedItems.length !== 1 ||
                    deletingJob ||
                    startingExecution
                  } // Enable only when one item is selected and not busy
                >
                  Delete Selected Job
                </Button>
                <Button
                  variant="normal" // Changed variant for consistency
                  onClick={handleStartExecutionClick}
                  disabled={
                    selectedItems.length !== 1 ||
                    startingExecution ||
                    deletingJob ||
                    // Optionally disable if job status is not 'Pending' or similar
                    selectedItems[0]?.status === AssessmentStatus.Assessing ||
                    selectedItems[0]?.status === AssessmentStatus.Pending
                  } // Disable if not exactly one selected, busy, or not in a startable state
                  loading={startingExecution} // Show loading state
                >
                  Requeue Execution
                </Button>
                <Button
                  variant="primary"
                  onClick={handleCreateClick}
                  disabled={deletingJob || startingExecution} // Disable if busy
                >
                  Create Verification Job
                </Button>
              </SpaceBetween>
            }
          >
            Verification Jobs
          </Header>
          {/* Error loading jobs */}
          {jobsError && (
            <Alert
              statusIconAriaLabel="Error"
              type="error"
              header="Failed to load verification jobs"
            >
              {jobsError || "An unknown error occurred."}{" "}
              <Button onClick={refetch} disabled={loadingJobs}>
                Retry
              </Button>
            </Alert>
          )}
          {/* Error during delete - Use deleteError from the hook */}
          {deleteError && (
            <Alert
              statusIconAriaLabel="Error"
              type="error"
              header="Failed to delete verification job"
              // Consider if dismissible is needed; error might clear on next action
            >
              {deleteError || "An unknown error occurred during deletion."}
            </Alert>
          )}
          {/* Error during start execution */}
          {startExecutionError && (
            <Alert
              statusIconAriaLabel="Error"
              type="error"
              header="Failed to start verification job execution"
              // dismissible // Consider if needed
            >
              {startExecutionError ||
                "An unknown error occurred while starting execution."}
            </Alert>
          )}
        </SpaceBetween>
      }
    >
      <Table
        selectedItems={selectedItems}
        onSelectionChange={({ detail }) =>
          setSelectedItems(detail.selectedItems)
        }
        columnDefinitions={[
          {
            id: "id",
            header: "Job ID",
            cell: (item) => (
              <Link href={`/job/${item.id}`}>{item.id || "-"}</Link> // Link to details page
            ),
            sortingField: "id",
            isRowHeader: true,
          },
          {
            id: "collection",
            header: "Collection",
            cell: (item) => (
              <Link target="_blank" href={`/collection/${item.collectionId}`}>
                {item.collectionName || "-"}
              </Link>
            ), // Corrected property name
            sortingField: "collectionName", // Corrected property name
          },
          {
            id: "sorCount",
            header: "Items",
            cell: (item) => (item.items ? item.items?.length : 0), // Round to 5 decimal places
            sortingField: "sorCount",
          },
          {
            id: "status",
            header: "Status",
            cell: (item) => renderStatus(item.status), // Use renderStatus function
            sortingField: "status",
          },
          {
            id: "cost",
            header: "Cost",
            cell: (item) => `$${(item.cost ?? 0).toFixed(6)}`, // Round to 5 decimal places
            sortingField: "cost",
          },
          {
            id: "createdAt",
            header: "Created At",
            cell: (item) =>
              item.createdAt // Corrected property name
                ? new Date(item.createdAt * 1000).toLocaleString() // Corrected property name
                : "-",
            sortingField: "createdAt", // Corrected property name
          },
          // Removed the actions column as delete is now handled by the header button
        ]}
        stripedRows
        items={filteredJobs}
        loading={loadingJobs} // Use renamed loading state
        loadingText="Loading verification jobs..."
        selectionType="single"
        trackBy="id"
        empty={
          <Box textAlign="center" color="inherit">
            <b>No verification jobs found</b>
            <Box padding={{ bottom: "s" }} variant="p" color="inherit">
              No verification jobs match the criteria.
            </Box>
            {/* Optionally add a create button here too */}
          </Box>
        }
        filter={
          <TextFilter
            filteringPlaceholder="Find jobs by ID, status, or collection ID"
            filteringText={filteringText}
            onChange={({ detail }) => setFilteringText(detail.filteringText)}
            disabled={loadingJobs} // Use renamed loading state
          />
        }
        header={
          <Header
            counter={
              selectedItems.length
                ? `(${selectedItems.length}/${filteredJobs.length})`
                : `(${filteredJobs.length})`
            }
            // Add actions for selected items if needed (e.g., delete, update status)
          >
            Jobs
          </Header>
        }
        pagination={
          // TODO: Implement proper pagination based on API response
          <Pagination currentPageIndex={1} pagesCount={1} />
        }
        // Add sorting configuration if needed
      />
      {/* Delete Confirmation Modal */}
      <Modal
        visible={isDeleteModalVisible}
        header="Delete Verification Job"
        closeAriaLabel="Close modal"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="link"
                onClick={handleCancelDelete}
                disabled={deletingJob || startingExecution} // Disable while busy
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleConfirmDelete}
                loading={deletingJob} // Show loading state
                disabled={startingExecution} // Disable while busy
              >
                Delete
              </Button>
            </SpaceBetween>
          </Box>
        }
        onDismiss={handleCancelDelete}
      >
        Are you sure you want to delete verification job{" "}
        <strong>{jobToDeleteId}</strong>? This action cannot be undone.
      </Modal>
    </ContentLayout>
  );
};
