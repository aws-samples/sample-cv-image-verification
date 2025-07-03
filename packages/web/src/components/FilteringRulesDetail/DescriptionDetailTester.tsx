import {
  ExpandableSection,
  SpaceBetween,
  Container,
  FormField,
  // Input, // Removed unused import
  Button,
  Alert,
  Spinner,
  Box,
  Modal, // Import Modal
  // Grid, // Removed unused import
} from "@cloudscape-design/components";
import { FC, useState, useCallback, useEffect, useRef } from "react"; // Import useRef
import { useDropzone, FileWithPath } from "react-dropzone";
import {
  useGenerateUploadPresignedUrls,
  useTestDescriptionPrompt,
} from "../../hooks/Items";
import axios from "axios";
import {
  GenerateUploadUrlsResponse,
  PresignedFileUrl,
  TestDescriptionFilterPromptResponse,
  TotalCheckItemResult, // Correct type for URL items
} from "@aws-samples/cv-verification-api-client/src";

interface DescriptionDetailTesterProps {
  description: string; // Add description prop
  selectedAgentIds?: string[];
}

export const DescriptionDetailTester: FC<DescriptionDetailTesterProps> = ({
  description,
  selectedAgentIds,
}) => {
  // Store files with preview URLs
  const [filesWithPreview, setFilesWithPreview] = useState<
    (FileWithPath & { preview: string })[]
  >([]);
  // Store mapping from S3 Key to Preview URL
  const [s3KeyToPreviewMap, setS3KeyToPreviewMap] = useState<
    Map<string, string>
  >(new Map());
  const [isUploading, setIsUploading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] =
    useState<TestDescriptionFilterPromptResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // State for image modal
  const [isImageModalVisible, setIsImageModalVisible] = useState(false);
  const [selectedImageUrl, setSelectedImageUrl] = useState<string | null>(null);

  // Ref to keep track of current preview URLs for cleanup
  const currentPreviewUrlsRef = useRef<string[]>([]);

  const generateUploadUrls = useGenerateUploadPresignedUrls();
  const testDescriptionPrompt = useTestDescriptionPrompt();

  const onDrop = useCallback(
    (acceptedFiles: FileWithPath[]) => {
      // Revoke previous previews using the ref's value before update
      currentPreviewUrlsRef.current.forEach(URL.revokeObjectURL);

      // Generate preview URLs
      const filesWithGeneratedPreview = acceptedFiles.map((file) =>
        Object.assign(file, {
          preview: URL.createObjectURL(file),
          // No s3Key needed here anymore
        })
      );
      setFilesWithPreview(filesWithGeneratedPreview);
      // Update the ref with the new preview URLs
      currentPreviewUrlsRef.current = filesWithGeneratedPreview.map(
        (f) => f.preview
      );
      setS3KeyToPreviewMap(new Map()); // Clear the key map on new files
      setTestResult(null); // Clear previous results on new files
      setError(null); // Clear previous errors
    },
    [] // No dependency needed as we use ref for revocation
  );

  // Clean up preview URLs on unmount only using the ref
  useEffect(() => {
    // Return a cleanup function that runs only on unmount
    return () => {
      console.log(
        "Unmounting, revoking URLs from ref:",
        currentPreviewUrlsRef.current
      ); // Optional: for debugging
      currentPreviewUrlsRef.current.forEach(URL.revokeObjectURL);
    };
  }, []); // Empty dependency array ensures cleanup runs only on unmount

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".jpeg", ".jpg", ".png", ".gif"],
    },
  });

  const handleTest = async () => {
    // Use filesWithPreview for checks and mapping
    if (filesWithPreview.length === 0 || !description) {
      setError(
        "Please select at least one image file to test the description."
      );
      return;
    }

    setError(null);
    setTestResult(null);
    setIsUploading(true);
    setIsTesting(false);

    try {
      // 1. Get presigned URLs using filenames from filesWithPreview
      const filenames = filesWithPreview.map((file) => file.name);
      const presignedUrlResponse: GenerateUploadUrlsResponse | undefined =
        await generateUploadUrls.mutateAsync(filenames);

      // Use .urls instead of .items
      if (
        !presignedUrlResponse?.urls ||
        presignedUrlResponse.urls.length === 0
      ) {
        throw new Error("Failed to get upload URLs.");
      }

      // Use PresignedFileUrl for item type
      const uploadPromises = presignedUrlResponse.urls.map(
        async (item: PresignedFileUrl) => {
          // Find file in filesWithPreview
          const file = filesWithPreview.find((f) => f.name === item.filename);
          if (!file) {
            throw new Error(
              `File ${item.filename} not found in accepted files.`
            );
          }
          // Using axios for potentially better error handling and progress events if needed later
          // Use item.presignedUrl instead of item.uploadUrl
          await axios.put(item.presignedUrl, file, {
            headers: {
              "Content-Type": file.type,
            },
          });
          // Use item.s3Key
          return item.s3Key; // Return the S3 key for the next step
        }
      );

      // 2. Upload files
      const s3Keys = await Promise.all(uploadPromises); // Get S3 keys from uploads

      // Create the S3 Key to Preview URL map after uploads complete
      const keyToPreviewMap = new Map<string, string>();
      presignedUrlResponse.urls.forEach((item: PresignedFileUrl) => {
        // Add type annotation for clarity
        const file = filesWithPreview.find((f) => f.name === item.filename);
        if (file && item.s3Key) {
          // Ensure s3Key exists
          keyToPreviewMap.set(item.s3Key, file.preview); // Use s3Key as the map key
        }
      });
      setS3KeyToPreviewMap(keyToPreviewMap); // Set the map state

      setIsUploading(false);
      setIsTesting(true);

      // 3. Test prompt (s3Keys array is already available)
      const testResponse = await testDescriptionPrompt.mutateAsync({
        description,
        imageS3Keys: s3Keys,
        agentIds: selectedAgentIds || [],
      });

      if (testResponse) {
        setTestResult(testResponse);
      } else {
        // Handle the case where the API call returns undefined
        throw new Error(
          "Test prompt API call did not return a valid response."
        );
      }
    } catch (err) {
      console.error("Testing failed:", err);
      const errorMessage =
        err instanceof Error ? err.message : "An unknown error occurred.";
      setError(`Testing failed: ${errorMessage}`);
      setTestResult(null); // Clear results on error
    } finally {
      setIsUploading(false);
      setIsTesting(false);
    }
  };

  // Modal handlers
  const openImageModal = (imageUrl: string) => {
    setSelectedImageUrl(imageUrl);
    setIsImageModalVisible(true);
  };

  const closeImageModal = () => {
    setSelectedImageUrl(null);
    setIsImageModalVisible(false);
  };

  // Handle file removal
  const handleRemoveFile = (
    fileToRemove: FileWithPath & { preview: string },
    event: React.MouseEvent
  ) => {
    event.stopPropagation(); // Prevent triggering modal open

    // Revoke the object URL
    URL.revokeObjectURL(fileToRemove.preview);

    // Filter out the removed file
    const newFilesWithPreview = filesWithPreview.filter(
      (file) => file !== fileToRemove
    );
    setFilesWithPreview(newFilesWithPreview);

    // Update the ref
    currentPreviewUrlsRef.current = newFilesWithPreview.map((f) => f.preview);

    // Clear dependent states
    setS3KeyToPreviewMap(new Map());
    setTestResult(null);
    setError(null); // Also clear errors if input changes
  };

  // Render thumbnails
  const thumbs = filesWithPreview.map((file) => (
    <div
      key={file.name}
      onClick={() => openImageModal(file.preview)} // Add onClick
      style={{
        position: "relative", // Needed for absolute positioning of delete button
        cursor: "pointer",
        display: "inline-flex",
        borderRadius: 2,
        border: "1px solid #eaeaea",
        marginBottom: 8,
        marginRight: 8,
        width: 100,
        height: 100,
        padding: 4,
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", minWidth: 0, overflow: "hidden" }}>
        <img
          src={file.preview}
          style={{ display: "block", width: "auto", height: "100%" }}
          // REMOVED onLoad revocation - useEffect handles cleanup
        />
        {/* Delete Button */}
        <span
          onClick={(e) => handleRemoveFile(file, e)}
          style={{
            position: "absolute",
            top: "2px",
            right: "2px",
            background: "rgba(0, 0, 0, 0.5)",
            color: "white",
            borderRadius: "50%",
            width: "18px",
            height: "18px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "12px",
            lineHeight: "1",
            cursor: "pointer",
            fontWeight: "bold",
          }}
          title="Remove file"
        >
          X
        </span>
      </div>
    </div>
  ));

  return (
    <ExpandableSection
      headerInfo="This allows you to test descriptions against a set of images uploaded."
      headerText="Description Tester"
    >
      <SpaceBetween size="m">
        {/* Remove FormField and Input for description */}
        <FormField
          label="Upload Images"
          description="Drag 'n' drop some image files here, or click to select files."
        >
          <Container>
            <div
              {...getRootProps()}
              style={{
                border: `2px dashed ${isDragActive ? "blue" : "#ccc"}`,
                padding: "20px",
                textAlign: "center",
                cursor: "pointer",
              }}
            >
              <input {...getInputProps()} />
              {isDragActive ? (
                <p>Drop the files here ...</p>
              ) : (
                <p>Drag 'n' drop image files here, or click to select</p>
              )}
            </div>
            {/* Display thumbnails */}
            {filesWithPreview.length > 0 && (
              <Box margin={{ top: "s" }}>
                <h4>Selected files preview:</h4>
                <aside
                  style={{
                    display: "flex",
                    flexDirection: "row",
                    flexWrap: "wrap",
                    marginTop: 16,
                  }}
                >
                  {thumbs}
                </aside>
              </Box>
            )}
          </Container>
        </FormField>

        <Button
          variant="primary"
          onClick={handleTest}
          disabled={
            // Use filesWithPreview for disabled check
            isUploading ||
            isTesting ||
            filesWithPreview.length === 0 ||
            !description
          }
        >
          {isUploading && <Spinner />}
          {isTesting && <Spinner />}
          {!isUploading && !isTesting && "Test Description"}
          {isUploading && " Uploading..."}
          {isTesting && " Testing..."}
        </Button>

        {error && (
          <Alert statusIconAriaLabel="Error" type="error">
            {error}
          </Alert>
        )}

        {testResult?.response?.response?.items && ( // Check nested structure
          <Container>
            <SpaceBetween size="s">
              <Box>
                <strong>Overall Result:</strong>{" "}
                {testResult.response.response.items.some(
                  (item) => item.imageFound
                ) ? (
                  <span style={{ color: "green" }}>Pass (Image Found)</span>
                ) : (
                  <span style={{ color: "red" }}>Fail (No Image Found)</span>
                )}
              </Box>
              {testResult.response.response.items[0]?.reasoning && (
                <Box>
                  <strong>Reason (Primary):</strong>{" "}
                  {testResult.response.response.items[0].reasoning}
                </Box>
              )}
              {testResult.response.response.items.length > 0 && (
                <Box>
                  <strong>Item Check Details:</strong>
                  <ul>
                    {testResult.response.response.items.map(
                      (
                        itemResult: TotalCheckItemResult, // Use correct type
                        index: number
                      ) => (
                        <li key={itemResult.itemId || index}>
                          {" "}
                          {/* Use sorId as key if available */}
                          Check {index + 1}:{" "}
                          {itemResult.imageFound ? (
                            <>
                              <span style={{ color: "green" }}>
                                Image Found
                              </span>
                              {/* Find and render matching previews for all fileIds */}
                              {itemResult.fileIds?.map((fileId) => {
                                const matchedPreviewUrl =
                                  s3KeyToPreviewMap.get(fileId);
                                if (matchedPreviewUrl) {
                                  return (
                                    <img
                                      key={fileId} // Add key for list rendering
                                      src={matchedPreviewUrl}
                                      alt={`Match for ${itemResult.itemId} - ${fileId}`}
                                      onClick={() =>
                                        openImageModal(matchedPreviewUrl)
                                      }
                                      style={{
                                        height: "20px",
                                        width: "auto",
                                        marginLeft: "8px",
                                        verticalAlign: "middle",
                                        cursor: "pointer",
                                      }}
                                    />
                                  );
                                }
                                return null; // Return null if no matching preview URL for this fileId
                              })}
                            </>
                          ) : (
                            <span style={{ color: "red" }}>No Image Found</span>
                          )}{" "}
                          - {itemResult.reasoning} {/* Use reasoning */}
                          {itemResult.confidence &&
                            ` (Confidence: ${itemResult.confidence.toFixed(
                              2
                            )})`}
                          {/* Display fileIds only if image was not found, otherwise thumbnail is shown */}
                          {itemResult.fileIds &&
                            itemResult.fileIds.length > 0 &&
                            !itemResult.imageFound &&
                            ` (File IDs: ${itemResult.fileIds.join(", ")})`}
                          {itemResult.location &&
                            ` (Location: ${itemResult.location})`}
                        </li>
                      )
                    )}
                  </ul>
                </Box>
              )}
            </SpaceBetween>
          </Container>
        )}

        {/* Image Modal */}
        <Modal
          onDismiss={closeImageModal}
          visible={isImageModalVisible}
          closeAriaLabel="Close modal"
          size="large"
          header="Image Preview"
          footer={
            <Box float="right">
              <Button variant="primary" onClick={closeImageModal}>
                Close
              </Button>
            </Box>
          }
        >
          {selectedImageUrl && (
            <img
              src={selectedImageUrl}
              style={{
                maxWidth: "100%",
                maxHeight: "80vh",
                display: "block",
                margin: "auto",
              }}
              alt="Selected Preview"
            />
          )}
        </Modal>
      </SpaceBetween>
    </ExpandableSection>
  );
};
