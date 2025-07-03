import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  Container,
  Form,
  FormField,
  Header,
  // Input, // Replaced with Autosuggest
  SpaceBetween,
  Textarea,
  Autosuggest, // Import Autosuggest
  Cards,
  Badge,
  // FileUpload, // Replaced with react-dropzone
  Link,
  Alert,
  Select,
  Table,
  Modal,
  Grid,
  Icon, // Import Icon for dropzone
} from "@cloudscape-design/components";
import { useDropzone } from "react-dropzone"; // Import react-dropzone
import { v4 as uuidv4 } from "uuid";
import { useQueryClient } from "@tanstack/react-query"; // Import useQueryClient
import {
  Collection,
  CollectionFile,
  CollectionFileStatus,
  CreateCollectionRequest,
  Item,
  ItemInstance,
  UpdateCollectionRequest,
  AssessmentStatus,
} from "@aws-samples/cv-verification-api-client/src";
import {
  useAddFileToCollection,
  useAddressAutocomplete,
  useCreateCollection,
  useGetCollectionFilePresignedUrls,
  usePresignCollectionsFileUpload,
  useUpdateCollection,
} from "../../hooks/Collections";
import { useGetAllItems } from "../../hooks/Items";

// --- Removed Map Component ---

interface CollectionDetailsProps {
  collection?: Collection;
  onSave?: (collectionId: string) => void;
  onCancel?: () => void;
}

const WorkOrderDetails: React.FC<CollectionDetailsProps> = ({
  collection,
  onSave,
  onCancel,
}) => {
  const queryClient = useQueryClient(); // Get query client instance
  const isEditing = !!collection;

  const [description, setDescription] = useState<string>(
    collection?.description || ""
  );
  const [address, setAddress] = useState<string>(collection?.address || ""); // Initialize with collection address
  const [addressQuery, setAddressQuery] = useState<string>(
    collection?.address || ""
  ); // State for Autosuggest input
  const [files, setFiles] = useState<CollectionFile[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [availableItems, setAvailableItems] = useState<Item[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [associatedItems, setAssociatedItems] = useState<ItemInstance[]>([]);
  const [presignedUrls, setPresignedUrls] = useState<Record<string, string>>(
    {}
  );
  const [isImageModalOpen, setIsImageModalOpen] = useState<boolean>(false);
  const [selectedImageUrl, setSelectedImageUrl] = useState<string | null>(null);
  const [selectedImageFilename, setSelectedImageFilename] = useState<
    string | null
  >(null); // Added state for filename

  // --- Autocomplete Hook ---
  // Debounce the query input to avoid excessive API calls
  const [debouncedAddressQuery, setDebouncedAddressQuery] =
    useState(addressQuery);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedAddressQuery(addressQuery);
    }, 3000); // 3 seconds debounce time

    return () => {
      clearTimeout(handler);
    };
  }, [addressQuery]);

  const { data: addressSuggestions, isLoading: isLoadingSuggestions } =
    useAddressAutocomplete(debouncedAddressQuery);
  // --- End Autocomplete ---

  // --- Removed Get Coordinates Hook ---

  const { data: itemsData, isLoading: isLoadingItems } = useGetAllItems();
  useEffect(() => {
    if (itemsData) {
      // Check itemsData directly
      setAvailableItems(itemsData);
    }
  }, [itemsData]); // Re-added useEffect

  useEffect(() => {
    if (collection) {
      setDescription(collection.description || "");
      setAddress(collection.address || ""); // Set final address
      setAddressQuery(collection.address || ""); // Set initial query for Autosuggest
      setFiles(collection.files || []);
      const initialItemInstances = (collection.items || []).map(
        (item: Item): ItemInstance => ({
          // Create a SorInstance-like object for the UI state
          id: uuidv4(), // Use a temporary UI ID or item.id if unique enough for UI keys
          createdAt: item.createdAt,
          updatedAt: item.updatedAt,
          name: item.name,
          description: item.description,
          labelFilteringRulesApplied: item.labelFilteringRules || [],
          descriptionFilteringRulesApplied:
            item.descriptionFilteringRules || [],
          status: AssessmentStatus.Pending, // Default status for display
          itemId: item.id,
          // Add other SorInstance fields with defaults if needed by the UI table
          assessmentReasoning: undefined,
          confidence: undefined,
          resultsLog: undefined,
          clusterNumber: undefined,
          // address: collection.address, // Address is on the WorkOrder level
        })
      );
      setAssociatedItems(initialItemInstances);
      setUploadedFiles([]); // Clear any pending uploads if the collection changes
      setError(null); // Clear any previous errors
      setSelectedItemId(null); // Keep reset selection
      // Reset presigned URLs and modal state when collection changes
      setPresignedUrls({});
      setIsImageModalOpen(false);
      setSelectedImageUrl(null);
      setSelectedImageFilename(null); // Reset filename
    } else {
      // Reset fields if collection becomes undefined (e.g., navigating to create new)
      setDescription("");
      setAddress("");
      setAddressQuery(""); // Reset Autosuggest query
      setFiles([]);
      setAssociatedItems([]);
      setUploadedFiles([]);
      setError(null);
      setSelectedItemId(null);
      setPresignedUrls({});
      setIsImageModalOpen(false);
      setSelectedImageUrl(null);
      setSelectedImageFilename(null); // Reset filename
    }
  }, [collection]);

  // Fetch presigned URLs when collection ID is available
  const { data: fetchedUrls, isLoading: isLoadingUrls } =
    useGetCollectionFilePresignedUrls(collection?.id);

  useEffect(() => {
    if (fetchedUrls) {
      setPresignedUrls(fetchedUrls);
    }
  }, [fetchedUrls]);

  const handleAddItem = () => {
    if (!selectedItemId) return;

    const itemToAdd = availableItems.find((item) => item.id === selectedItemId);
    if (!itemToAdd) return; // Should not happen if selectedItemId is valid

    // Prevent adding duplicates based on itemId
    if (associatedItems.some((item) => item.itemId === itemToAdd.id)) {
      setError(
        `Item "${itemToAdd.name} - ${itemToAdd.description}" is already added.`
      );
      return;
    }

    // Create a temporary SorInstance-like structure for display
    // Note: We only send itemIds on create, not full SorInstance
    const newItemInstance: ItemInstance = {
      // These fields are placeholders for UI display, not sent to backend directly
      id: uuidv4(), // Temporary ID for UI key
      createdAt: Math.floor(Date.now() / 1000),
      updatedAt: Math.floor(Date.now() / 1000),
      name: itemToAdd.name,
      clusterNumber: itemToAdd.clusterNumber,
      description: itemToAdd.description,
      labelFilteringRulesApplied: [], // Placeholder - Corrected case
      descriptionFilteringRulesApplied: [], // Placeholder - Corrected case
      status: AssessmentStatus.Pending, // Default status
      itemId: itemToAdd.id, // The important part for create request
    };

    setAssociatedItems((prev) => [...prev, newItemInstance]);
    setSelectedItemId(null); // Reset select
    setError(null); // Clear any previous error
  };

  const handleRemoveItem = (itemInstanceIdToRemove: string) => {
    setAssociatedItems((prev) =>
      prev.filter((item) => item.id !== itemInstanceIdToRemove)
    );
  };
  const { mutateAsync: createCollection, isPending: isCreating } =
    useCreateCollection();
  const { mutateAsync: updateCollection, isPending: isUpdating } =
    useUpdateCollection(collection?.id);
  // const { data: itemsData, isLoading: isLoadingItems } = useListSors(); // Moved up
  const { mutateAsync: presignUpload, isPending: isPresigning } =
    usePresignCollectionsFileUpload(
      // Also track presign pending state
      collection?.id
    );
  const { mutateAsync: addFileToCollection, isPending: isAddingFile } =
    useAddFileToCollection(
      // Also track add file pending state
      collection?.id
    );

  // Combine all relevant loading/pending states
  const isLoading =
    isCreating ||
    isUpdating ||
    uploading ||
    isLoadingItems ||
    isLoadingUrls ||
    isPresigning ||
    isAddingFile ||
    isLoadingSuggestions; // Include suggestion loading state

  // --- Dropzone Hook ---
  const onDrop = React.useCallback(
    (acceptedFiles: File[]) => {
      if (!isEditing) {
        setError("Files can only be added after the collection is created.");
        return;
      }
      setError(null);
      // Append new files to the existing uploadedFiles state
      setUploadedFiles((prevFiles) => [...prevFiles, ...acceptedFiles]);
    },
    [isEditing] // Re-create callback if isEditing changes
  );

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isFocused,
    isDragAccept,
    isDragReject,
  } = useDropzone({
    onDrop,
    disabled: !isEditing || isLoading, // Disable when not editing or loading
    // You can add accept prop here for specific file types, e.g., accept: { 'image/*': [] }
  });

  // Style the dropzone based on its state
  const dropzoneStyle: React.CSSProperties = React.useMemo(
    () => ({
      flex: 1,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "20px",
      borderWidth: 2,
      borderRadius: 2,
      borderColor: isDragAccept
        ? "#00e676"
        : isDragReject
        ? "#ff1744"
        : isFocused
        ? "#2196f3"
        : "#eeeeee",
      borderStyle: "dashed",
      backgroundColor: isDragActive ? "#fafafa" : "#ffffff",
      color: "#bdbdbd",
      outline: "none",
      transition: "border .24s ease-in-out, background-color .24s ease-in-out",
      curitem: !isEditing || isLoading ? "not-allowed" : "pointer",
      opacity: !isEditing || isLoading ? 0.5 : 1,
    }),
    [isDragActive, isFocused, isDragAccept, isDragReject, isEditing, isLoading]
  );
  // --- End Dropzone Hook ---

  const uploadFile = async (file: File): Promise<CollectionFile | null> => {
    try {
      // Only execute presignUpload if collectionId exists (edit mode)
      const presignResponse = await presignUpload({
        contentType: file.type,
        filename: file.name,
      });

      // --- Handle potential null response and check properties ---
      if (
        !presignResponse ||
        !presignResponse.presignedUrl ||
        !presignResponse.fileMetadata
      ) {
        // Log the actual response for debugging if needed
        console.error("Invalid presign response:", presignResponse);
        throw new Error("Failed to get valid presigned URL or metadata");
      }
      // --- End check ---

      // Upload to S3
      const uploadUrl = presignResponse.presignedUrl; // Safe to access now
      const response = await fetch(uploadUrl, {
        method: "PUT",
        body: file,
        headers: {
          "Content-Type": file.type,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to upload file");
      }

      // Extract metadata from the presign response - type assertion might still be needed
      // depending on the generated API client types, but the existence check above helps.
      const metadata = presignResponse.fileMetadata as
        | {
            id: string; // Assuming these properties exist based on previous code
            created_at: number; // snake_case from backend dict
            s3_key: string; // snake_case from backend dict
            content_type: string;
            filename: string;
          }
        | undefined; // Type assertion based on backend structure

      if (!metadata) {
        throw new Error("File metadata missing from presign response");
      }

      const fileDataForHook = {
        id: metadata.id, // Use the ID from metadata
        createdAt: metadata.created_at, // Use createdAt from metadata
        s3Key: metadata.s3_key, // Map snake_case to camelCase for the hook input
        contentType: metadata.content_type, // Use contentType from metadata
        filename: metadata.filename, // Use filename from metadata
        description: "", // Default description
        status: AssessmentStatus.NeedsReview, // Use the AssessmentStatus enum as expected by the API request model
        // statusReasoning is optional and not included here
      };

      // Only execute addFileToWorkOrder if collectionId exists (edit mode)
      const newWorkOrderFile: CollectionFile = {
        id: fileDataForHook.id,
        createdAt: fileDataForHook.createdAt,
        s3Key: fileDataForHook.s3Key,
        contentType: fileDataForHook.contentType,
        filename: fileDataForHook.filename,
        description: fileDataForHook.description,
        size: file.size,
        // status: fileDataForHook.status, // Removed: status is not part of WorkOrderFile type
        // statusReasoning: undefined, // Explicitly undefined if not set
      };

      if (collection?.id) {
        await addFileToCollection(fileDataForHook); // Pass the correctly structured data
      }

      // Return the newly created WorkOrderFile structure
      // State update and query invalidation moved to handleSubmit
      return newWorkOrderFile;
    } catch (err) {
      console.error("Error uploading file:", err);
      setError(`Failed to upload file: ${file.name}`);
      return null;
    }
  };

  const handleSubmit = async () => {
    setError(null);
    setUploading(true);
    let uploadsAttempted = false; // Declare outside try block

    try {
      // Upload files if any
      const uploadedFileRecords: CollectionFile[] = [];
      // Flag to track if uploads were done - moved declaration outside

      if (uploadedFiles.length > 0 && collection?.id) {
        // Ensure collection.id exists for uploads
        uploadsAttempted = true;
        for (const file of uploadedFiles) {
          const fileRecord = await uploadFile(file);
          if (fileRecord) {
            uploadedFileRecords.push(fileRecord);
          }
        }

        // --- Update state and invalidate query ONCE after all uploads ---
        if (uploadedFileRecords.length > 0) {
          setFiles((prevFiles) => [...prevFiles, ...uploadedFileRecords]);
          // Invalidate the query to refetch presigned URLs after all uploads are processed
          queryClient.invalidateQueries({
            queryKey: ["collection", collection.id, "files", "presignedUrls"],
          });
        }
        // --- End batch update ---
      }

      if (isEditing && collection) {
        // Update existing collection
        // Update existing collection - files are added via addFileToWorkOrder hook now
        const updateRequest: UpdateCollectionRequest = {
          description,
          address,
          // No need to pass files here, addFileToWorkOrder handles it.
        };

        const response = await updateCollection(updateRequest);
        if (response && onSave) {
          onSave(collection.id);
        }
      } else {
        // Create new collection
        // --- Validation: Ensure at least one item is selected ---
        if (associatedItems.length === 0) {
          setError(
            "Please select at least one item before creating the collection."
          );
          setUploading(false); // Reset uploading state
          return; // Stop submission
        }
        // --- End Validation ---

        const createRequest: CreateCollectionRequest = {
          description,
          address,
          files: uploadedFileRecords, // Assuming create handles initial files
          itemIds: associatedItems.map((item) => item.itemId), // Corrected property name: itemId
        };

        const response = await createCollection(createRequest);
        if (response && onSave && response.collection.id) {
          onSave(response.collection.id);
        }
      }
    } catch (err) {
      console.error("Error saving collection:", err);
      setError("Failed to save collection");
    } finally {
      setUploading(false);
      // Clear the pending upload list only if uploads were actually attempted
      if (uploadsAttempted) {
        setUploadedFiles([]);
      }
    }
  };

  const getStatusBadge = (
    fileStatus: CollectionFileStatus | AssessmentStatus | undefined | null
  ) => {
    if (!fileStatus) return <Badge color="grey">Pending</Badge>;

    // Convert status to string for comparison
    const statusStr = String(fileStatus);

    // Check against known values
    if (statusStr === AssessmentStatus.Approved) {
      return <Badge color="green">Approved</Badge>;
    } else if (statusStr === AssessmentStatus.Rejected) {
      return <Badge color="red">Rejected</Badge>;
    } else if (
      statusStr === AssessmentStatus.NeedsReview ||
      statusStr === CollectionFileStatus.NeedsReview
    ) {
      return <Badge color="blue">Needs Review</Badge>;
    } else if (statusStr === AssessmentStatus.Assessing) {
      return <Badge color="blue">Assessing</Badge>;
    } else if (statusStr === CollectionFileStatus.Relevant) {
      return <Badge color="green">Relevant</Badge>;
    } else if (statusStr === CollectionFileStatus.Ignored) {
      return <Badge color="grey">Ignored</Badge>;
    }

    return <Badge color="grey">Pending</Badge>;
  };

  return (
    <Container>
      <SpaceBetween size="l">
        <Header variant="h2">
          {isEditing ? "Edit Collection" : "Create Collection"}
        </Header>

        {error && (
          <Alert
            type="error"
            dismissible={true}
            onDismiss={() => setError(null)}
          >
            {error}
          </Alert>
        )}

        <Form
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={onCancel} disabled={isLoading}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleSubmit}
                disabled={isLoading}
                loading={isLoading}
              >
                {isEditing ? "Save changes" : "Create collection"}
              </Button>
            </SpaceBetween>
          }
        >
          <SpaceBetween size="l">
            <FormField label="Description">
              <Textarea
                value={description}
                onChange={({ detail }) => setDescription(detail.value)}
                disabled={isLoading}
                rows={3}
              />
            </FormField>

            <FormField
              description="Type to search for an address"
              label="Address"
            >
              <Autosuggest
                onChange={({ detail }) => {
                  setAddressQuery(detail.value); // Update the query state
                  // When user types freely, update the final address as well
                  // Or, you might only want to update final address on selection
                  setAddress(detail.value);
                }}
                value={addressQuery}
                options={(addressSuggestions || []).map((suggestion) => ({
                  label: suggestion.text,
                  value: suggestion.text, // Use text for both label and value
                  // You could add suggestion.placeId here if needed later
                }))}
                disableBrowserAutocorrect
                loadingText="Loading suggestions..."
                statusType={isLoadingSuggestions ? "loading" : "finished"}
                ariaLabel="Address search"
                placeholder="Enter address"
                empty="No suggestions found"
                disabled={isLoading}
                // Consider adding onSelect handler if you only want to set final address on selection
                onSelect={({ detail }) => {
                  if (detail.selectedOption?.value) {
                    setAddress(detail.selectedOption.value);
                    setAddressQuery(detail.selectedOption.value); // Sync query with selection
                  }
                }}
              />
              {/* --- Removed Map Display --- */}
            </FormField>

            <FormField label="Items">
              <SpaceBetween size="m">
                {/* Item Selection - Only enabled when creating */}
                {!isEditing ? (
                  <SpaceBetween direction="horizontal" size="xs">
                    <Select
                      selectedOption={
                        selectedItemId
                          ? {
                              label:
                                availableItems.find(
                                  (s) => s.id === selectedItemId
                                )?.name || "Select Item",
                              value: selectedItemId,
                            }
                          : null
                      }
                      onChange={({ detail }) =>
                        setSelectedItemId(detail.selectedOption.value || null)
                      }
                      options={availableItems
                        .filter(
                          (s) => !associatedItems.find((a) => a.itemId === s.id)
                        )
                        .map((item) => ({
                          label: item.name,
                          value: item.id,
                          description: `${item.description}${
                            item.clusterNumber
                              ? ` - Cluster ${item.clusterNumber?.toString()}`
                              : ""
                          }`,
                        }))}
                      loadingText="Loading items..."
                      statusType={isLoadingItems ? "loading" : "finished"}
                      placeholder="Select an item to add"
                      disabled={isLoading || availableItems.length === 0}
                    />
                    <Button
                      onClick={handleAddItem}
                      disabled={!selectedItemId || isLoading}
                    >
                      Add Item
                    </Button>
                  </SpaceBetween>
                ) : (
                  <Alert type="info" dismissible={false}>
                    Items cannot be modified for existing collections. Please
                    create a new collection to change associated items.
                  </Alert>
                )}

                <Table
                  columnDefinitions={[
                    {
                      id: "name",
                      header: "Item Name",
                      cell: (item) => (
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
                      cell: (item) => item.description,
                    },
                    {
                      id: "clusterNumber",
                      header: "Cluster Number",
                      cell: (item) => item.clusterNumber || "N/A",
                    },
                    {
                      id: "status",
                      header: "Status",
                      cell: (item) => getStatusBadge(item.status), // Reuse badge logic
                    },
                    {
                      id: "actions",
                      header: "Actions",
                      cell: (item) => (
                        <Button
                          variant="icon"
                          iconName="remove"
                          ariaLabel={`Remove Item ${item.name}`}
                          onClick={() => handleRemoveItem(item.id)}
                          disabled={isEditing} // Disable remove button in edit mode
                        />
                      ),
                    },
                  ]}
                  items={associatedItems}
                  loadingText="Loading associated items"
                  empty={
                    <Box textAlign="center" color="inherit">
                      <b>No items associated</b>
                      <Box
                        padding={{ bottom: "s" }}
                        variant="p"
                        color="inherit"
                      >
                        Add items using the selector above.
                      </Box>
                    </Box>
                  }
                  header={
                    <Header counter={`(${associatedItems.length})`}>
                      Associated Items
                    </Header>
                  }
                  variant="embedded" // Use embedded variant for better integration in form
                />
              </SpaceBetween>
            </FormField>

            <FormField
              label="Files"
              description="Upload files related to this collection. Click image thumbnails to enlarge."
            >
              <SpaceBetween size="m">
                {/* --- Start File Filtering and Display --- */}
                {(() => {
                  const imageFiles = files.filter((file) =>
                    file.contentType.startsWith("image/")
                  );
                  const otherFiles = files.filter(
                    (file) => !file.contentType.startsWith("image/")
                  );

                  // Updated to accept filename
                  const handleImageClick = (
                    url: string | null,
                    filename: string | null
                  ) => {
                    if (url && filename) {
                      setSelectedImageUrl(url);
                      setSelectedImageFilename(filename); // Store filename
                      setIsImageModalOpen(true);
                    }
                  };

                  return (
                    <>
                      {/* Image Thumbnails */}
                      {imageFiles.length > 0 && !uploading && (
                        <Box>
                          <Header variant="h3">Images</Header>
                          <Grid>
                            {imageFiles.map((file) => {
                              const url = presignedUrls[file.id];
                              return (
                                <Box
                                  key={file.id}
                                  textAlign="center"
                                  padding="xs"
                                >
                                  {isLoadingUrls ? ( // Check if URLs are still loading
                                    <Box
                                      color="text-status-inactive"
                                      padding="s"
                                    >
                                      Loading...
                                    </Box>
                                  ) : url ? ( // If not loading, check if URL exists
                                    <img
                                      src={url}
                                      alt={file.filename}
                                      style={{
                                        maxWidth: "100px",
                                        maxHeight: "100px",
                                        cursor: "pointer",
                                        border: "1px solid #ccc",
                                        objectFit: "cover",
                                      }}
                                      onClick={() =>
                                        handleImageClick(url, file.filename)
                                      } // Pass filename
                                      title={`Click to enlarge ${file.filename}`}
                                    />
                                  ) : (
                                    // If not loading and no URL, show placeholder/error
                                    <Box
                                      color="text-status-inactive"
                                      padding="s"
                                    >
                                      (No URL)
                                    </Box>
                                  )}
                                </Box>
                              );
                            })}
                          </Grid>
                        </Box>
                      )}

                      {/* Other Files */}
                      {otherFiles.length > 0 && (
                        <Cards
                          cardDefinition={{
                            sections: [
                              {
                                content: (item: CollectionFile) =>
                                  item.filename,
                              },
                            ],
                          }}
                          cardsPerRow={[
                            { cards: 1 },
                            { minWidth: 400, cards: 2 },
                          ]}
                          items={otherFiles}
                          loadingText="Loading files"
                          empty={
                            <Box textAlign="center" color="inherit">
                              <b>No other files attached</b>
                            </Box>
                          }
                          header={
                            <Header
                              variant="h3"
                              counter={`(${otherFiles.length})`}
                            >
                              Other Attached Files (Ignored)
                            </Header>
                          }
                        />
                      )}

                      {/* Handle case where there are no files at all */}
                      {files.length === 0 && (
                        <Box textAlign="center" color="inherit">
                          <b>No files attached</b>
                          <Box
                            padding={{ bottom: "s" }}
                            variant="p"
                            color="inherit"
                          >
                            No files have been attached to this collection.
                          </Box>
                        </Box>
                      )}
                    </>
                  );
                })()}
                {/* --- End File Filtering --- */}

                {/* --- Start react-dropzone Implementation --- */}
                {isEditing ? (
                  <Box>
                    <div {...getRootProps({ style: dropzoneStyle })}>
                      <input {...getInputProps()} />
                      {isDragActive ? (
                        <p>Drop the files here ...</p>
                      ) : (
                        <SpaceBetween
                          size="xs"
                          direction="horizontal"
                          alignItems="center"
                        >
                          <Icon name="upload" />
                          <span>
                            Drag 'n' drop some files here, or click to select
                            files
                          </span>
                        </SpaceBetween>
                      )}
                    </div>
                    {/* Display list of files staged for upload */}
                    {uploadedFiles.length > 0 && (
                      <Box margin={{ top: "s" }}>
                        <Header variant="h3">Files to upload:</Header>{" "}
                        {/* Corrected variant */}
                        <ul style={{ listStyle: "none", paddingLeft: 0 }}>
                          {uploadedFiles.map((file, index) => (
                            <li
                              key={index}
                              style={{
                                display: "flex",
                                alignItems: "center",
                                marginBottom: "4px",
                              }}
                            >
                              <Icon name="file" /> {/* Removed style */}
                              <span style={{ marginLeft: "8px" }}>
                                {" "}
                                {/* Added span for spacing */}
                                {file.name} - {(file.size / 1024).toFixed(2)} KB
                              </span>
                              {/* Wrap button in span for positioning */}
                              <span style={{ marginLeft: "auto" }}>
                                <Button
                                  variant="icon"
                                  iconName="close"
                                  ariaLabel={`Remove ${file.name}`}
                                  onClick={() =>
                                    setUploadedFiles(
                                      uploadedFiles.filter(
                                        (_, i) => i !== index
                                      )
                                    )
                                  }
                                  disabled={isLoading}
                                  // Removed style prop from Button
                                />
                              </span>
                            </li>
                          ))}
                        </ul>
                      </Box>
                    )}
                  </Box>
                ) : (
                  <Box variant="p" color="text-status-info">
                    Files can only be uploaded once the collection has been
                    created.
                  </Box>
                )}
              </SpaceBetween>
            </FormField>
          </SpaceBetween>
        </Form>
      </SpaceBetween>

      {/* Image Modal */}
      <Modal
        onDismiss={() => {
          setIsImageModalOpen(false);
          setSelectedImageUrl(null);
          setSelectedImageFilename(null); // Reset filename on dismiss
        }}
        visible={isImageModalOpen}
        closeAriaLabel="Close modal"
        size="large" // Adjust size as needed
        header={selectedImageFilename || "Image Preview"} // Use filename in header
      >
        {selectedImageUrl && (
          <img
            src={selectedImageUrl}
            alt="Enlarged view"
            style={{ maxWidth: "100%", maxHeight: "70vh" }} // Adjust styling
          />
        )}
      </Modal>
    </Container>
  );
};

export default WorkOrderDetails;
