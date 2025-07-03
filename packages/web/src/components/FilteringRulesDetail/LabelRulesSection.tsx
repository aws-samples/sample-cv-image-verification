import React, { useState, useEffect } from "react";
import { Link } from "@cloudscape-design/components";
import {
  Box,
  Button,
  Header,
  Modal,
  SpaceBetween,
  Table,
  Pagination,
  TextFilter,
  FormField,
  Input,
  Form,
  ButtonDropdown,
  TokenGroup,
  Alert,
  FileUpload,
  ProgressBar,
} from "@cloudscape-design/components";
import { v4 as uuidv4 } from "uuid";
import { LabelFormErrors, defaultLabelRule } from "./types";
import { DeleteConfirmationModal } from "./DeleteConfirmationModal";
import {
  useTestLabelRules,
  useGenerateUploadPresignedUrls,
  useGenerateDownloadPresignedUrls,
} from "../../hooks/Items";
import {
  LabelFilteringRule,
  TestLabelFilteringRuleLabel,
} from "@aws-samples/cv-verification-api-client/src";

interface LabelRulesSectionProps {
  rules: LabelFilteringRule[];
  onRulesChange: (updatedRules: LabelFilteringRule[]) => void;
}

export const LabelRulesSection: React.FC<LabelRulesSectionProps> = ({
  rules: initialRules,
  onRulesChange,
}) => {
  const [labelFilteringRules, setLabelFilteringRules] = useState<
    LabelFilteringRule[]
  >([]);

  // Label Rule State
  const [labelModalVisible, setLabelModalVisible] = useState(false);
  const [testModalVisible, setTestModalVisible] = useState(false);
  const [isLabelEditMode, setIsLabelEditMode] = useState(false);
  const [currentLabelRule, setCurrentLabelRule] =
    useState<LabelFilteringRule | null>(null);
  const [labelCurrentPage, setLabelCurrentPage] = useState(1);
  const [labelFilterText, setLabelFilterText] = useState("");
  const [labelFormErrors, setLabelFormErrors] = useState<LabelFormErrors>({});
  const [selectedLabelItems, setSelectedLabelItems] = useState<
    LabelFilteringRule[]
  >([]);
  const [labelDeleteConfirmationVisible, setLabelDeleteConfirmationVisible] =
    useState(false);
  const [labelInputValue, setLabelInputValue] = useState(""); // For adding labels in modal

  const pageSize = 5;

  // Effect to update state when props change
  useEffect(() => {
    setLabelFilteringRules(initialRules);
  }, [initialRules]);

  // --- Label Rule Logic ---

  const filteredLabelRules = labelFilteringRules.filter((rule) => {
    if (!labelFilterText) return true;
    const searchText = labelFilterText.toLowerCase();
    const labelsText = rule.imageLabels?.join(", ").toLowerCase() || "";
    return (
      labelsText.includes(searchText) ||
      (rule.minConfidence?.toString() ?? "").includes(searchText) ||
      (rule.minImageSizePercent?.toString() ?? "").includes(searchText)
    );
  });

  const totalLabelPages = Math.ceil(filteredLabelRules.length / pageSize);
  const labelStartIndex = (labelCurrentPage - 1) * pageSize;
  const visibleLabelRules = filteredLabelRules.slice(
    labelStartIndex,
    labelStartIndex + pageSize
  );

  const handleCreateLabelRule = () => {
    setCurrentLabelRule({
      ...defaultLabelRule,
      id: "", // Temporary ID, will be replaced
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
    setIsLabelEditMode(false);
    setLabelFormErrors({});
    setLabelModalVisible(true);
  };

  const handleEditLabelRule = (rule: LabelFilteringRule) => {
    setCurrentLabelRule({ ...rule });
    setIsLabelEditMode(true);
    setLabelFormErrors({});
    setLabelModalVisible(true);
  };

  const handleDeleteLabelRules = (rulesToDelete: LabelFilteringRule[]) => {
    const updatedRules = labelFilteringRules.filter(
      (rule) => !rulesToDelete.some((deleteRule) => deleteRule.id === rule.id)
    );
    setLabelFilteringRules(updatedRules);
    setSelectedLabelItems([]);
    setLabelDeleteConfirmationVisible(false);

    if (
      labelCurrentPage > 1 &&
      updatedRules.length <= (labelCurrentPage - 1) * pageSize
    ) {
      setLabelCurrentPage(labelCurrentPage - 1);
    }

    onRulesChange(updatedRules); // Notify parent
  };

  const validateLabelForm = (): boolean => {
    const errors: LabelFormErrors = {};
    if (!currentLabelRule) return false;

    if (
      !currentLabelRule.imageLabels ||
      currentLabelRule.imageLabels.length === 0
    ) {
      errors.imageLabels = "At least one image label is required";
    }

    const confidence = currentLabelRule.minConfidence;
    if (
      confidence === undefined ||
      confidence === null ||
      isNaN(confidence) ||
      confidence < 0 ||
      confidence > 1
    ) {
      errors.minConfidence = "Confidence must be a number between 0 and 1";
    }

    const sizePercent = currentLabelRule.minImageSizePercent;
    if (
      sizePercent === undefined ||
      sizePercent === null ||
      isNaN(sizePercent) ||
      sizePercent < 0 ||
      sizePercent > 1
    ) {
      errors.minImageSizePercent =
        "Size percentage must be a number between 0 and 1";
    }

    setLabelFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveLabelRule = () => {
    if (!validateLabelForm() || !currentLabelRule) return;

    let updatedRules: LabelFilteringRule[];
    if (isLabelEditMode) {
      updatedRules = labelFilteringRules.map((rule) =>
        rule.id === currentLabelRule.id
          ? {
              ...currentLabelRule,
              createdAt: currentLabelRule.createdAt ?? Date.now(),
              updatedAt: Date.now(),
            }
          : rule
      );
    } else {
      const newRule: LabelFilteringRule = {
        ...currentLabelRule,
        id: uuidv4(),
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      updatedRules = [...labelFilteringRules, newRule];
    }

    setLabelFilteringRules(updatedRules);
    setLabelModalVisible(false);
    onRulesChange(updatedRules); // Notify parent
  };

  const handleLabelActionsClick = ({ detail }: { detail: { id: string } }) => {
    switch (detail.id) {
      case "edit":
        if (selectedLabelItems.length === 1) {
          handleEditLabelRule(selectedLabelItems[0]);
        }
        break;
      case "delete":
        if (selectedLabelItems.length > 0) {
          setLabelDeleteConfirmationVisible(true);
        }
        break;
    }
  };

  const handleAddLabel = () => {
    if (!currentLabelRule || !labelInputValue.trim()) return;
    const newLabel = labelInputValue.trim();
    if (!currentLabelRule.imageLabels?.includes(newLabel)) {
      setCurrentLabelRule({
        ...currentLabelRule,
        imageLabels: [...(currentLabelRule.imageLabels || []), newLabel],
      });
      setLabelInputValue("");
    }
  };

  return (
    <>
      <Table
        resizableColumns
        header={
          <Header
            counter={`(${labelFilteringRules.length})`}
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button onClick={() => setTestModalVisible(true)}>Test</Button>
                <ButtonDropdown
                  items={[
                    {
                      id: "edit",
                      text: "Edit",
                      disabled: selectedLabelItems.length !== 1,
                    },
                    {
                      id: "delete",
                      text: "Delete",
                      disabled: selectedLabelItems.length === 0,
                    },
                  ]}
                  onItemClick={handleLabelActionsClick}
                  disabled={selectedLabelItems.length === 0}
                >
                  Actions
                </ButtonDropdown>
                <Button variant="primary" onClick={handleCreateLabelRule}>
                  Create label rule
                </Button>
              </SpaceBetween>
            }
          >
            Label Filtering Rules
          </Header>
        }
        columnDefinitions={[
          {
            id: "imageLabels",
            header: "Image Labels",
            cell: (item: LabelFilteringRule) =>
              item.imageLabels && item.imageLabels.length > 0 ? (
                <TokenGroup
                  items={item.imageLabels
                    .filter((label) => !!label)
                    .map((label) => ({
                      label: label ?? "-",
                      value: label ?? "-",
                      dismissible: true,
                    }))}
                />
              ) : (
                "-"
              ),
            sortingField: "imageLabels",
          },
          {
            id: "minConfidence",
            header: "Min Confidence",
            cell: (item: LabelFilteringRule) =>
              item.minConfidence !== undefined && item.minConfidence !== null
                ? item.minConfidence.toFixed(2)
                : "N/A",
            sortingField: "minConfidence",
          },
          {
            id: "minImageSizePercent",
            header: "Min Size %",
            cell: (item: LabelFilteringRule) =>
              item.minImageSizePercent !== undefined &&
              item.minImageSizePercent !== null
                ? `${(item.minImageSizePercent * 100).toFixed(0)}%`
                : "N/A",
            sortingField: "minImageSizePercent",
          },
          {
            id: "createdAt",
            header: "Created",
            cell: (item: LabelFilteringRule) =>
              item.createdAt
                ? new Date(item.createdAt).toLocaleString()
                : "N/A",
            sortingField: "createdAt",
          },
          {
            id: "updatedAt",
            header: "Updated",
            cell: (item: LabelFilteringRule) =>
              item.updatedAt
                ? new Date(item.updatedAt).toLocaleString()
                : "N/A",
            sortingField: "updatedAt",
          },
        ]}
        items={visibleLabelRules}
        selectionType="multi"
        selectedItems={selectedLabelItems}
        onSelectionChange={({ detail }) =>
          setSelectedLabelItems(detail.selectedItems)
        }
        pagination={
          <Pagination
            currentPageIndex={labelCurrentPage}
            pagesCount={totalLabelPages}
            onChange={({ detail }) =>
              setLabelCurrentPage(detail.currentPageIndex)
            }
          />
        }
        filter={
          <TextFilter
            filteringText={labelFilterText}
            onChange={({ detail }) => setLabelFilterText(detail.filteringText)}
            filteringPlaceholder="Find label rules"
            countText={`${filteredLabelRules.length} matches`}
          />
        }
        empty={
          <Box textAlign="center" color="inherit">
            <b>No label filtering rules</b>
            <Box padding={{ bottom: "s" }} variant="p" color="inherit">
              No label filtering rules have been defined yet.
            </Box>
            <Button onClick={handleCreateLabelRule}>Create label rule</Button>
          </Box>
        }
      />

      {/* Create/Edit Label Rule Modal */}
      <Modal
        visible={labelModalVisible}
        onDismiss={() => setLabelModalVisible(false)}
        header={isLabelEditMode ? "Edit label rule" : "Create label rule"}
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="link"
                onClick={() => setLabelModalVisible(false)}
              >
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveLabelRule}>
                {isLabelEditMode ? "Save changes" : "Create rule"}
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        {currentLabelRule && (
          <Form>
            <FormField
              label="Image Labels"
              description="Add labels to filter on"
              errorText={labelFormErrors.imageLabels}
            >
              <SpaceBetween direction="vertical" size="xs">
                {currentLabelRule.imageLabels &&
                  currentLabelRule.imageLabels.length > 0 && (
                    <TokenGroup
                      items={currentLabelRule.imageLabels
                        .filter((label) => !!label)
                        .map((label) => ({
                          label: label ?? "-",
                          value: label ?? "-",
                          dismissible: true,
                        }))}
                      onDismiss={({ detail: { itemIndex } }) => {
                        if (!currentLabelRule) return;
                        const newLabels = [
                          ...(currentLabelRule.imageLabels || []),
                        ];
                        newLabels.splice(itemIndex, 1);
                        setCurrentLabelRule({
                          ...currentLabelRule,
                          imageLabels: newLabels,
                        });
                      }}
                    />
                  )}
                <SpaceBetween direction="horizontal" size="xs">
                  <Input
                    value={labelInputValue}
                    onChange={({ detail }) => setLabelInputValue(detail.value)}
                    placeholder="Type a label"
                  />
                  <Button onClick={handleAddLabel}>Add</Button>
                </SpaceBetween>
              </SpaceBetween>
            </FormField>
            <FormField
              label="Minimum Confidence"
              description="Threshold for label confidence (0.0 to 1.0)"
              errorText={labelFormErrors.minConfidence}
            >
              <Input
                type="number"
                step={0.01}
                value={currentLabelRule.minConfidence?.toString() ?? ""}
                onChange={({ detail }) => {
                  if (!currentLabelRule) return;
                  const value = detail.value;
                  const parsedValue = value === "" ? NaN : parseFloat(value);
                  const finalMinConfidence = isNaN(parsedValue)
                    ? defaultLabelRule.minConfidence
                    : parsedValue;
                  setCurrentLabelRule({
                    ...currentLabelRule,
                    minConfidence: finalMinConfidence,
                  });
                }}
              />
            </FormField>
            <FormField
              label="Minimum Image Size Percentage"
              description="Minimum area percentage that the labeled object must occupy (0.0 to 1.0)"
              errorText={labelFormErrors.minImageSizePercent}
            >
              <Input
                type="number"
                step={0.01}
                value={currentLabelRule.minImageSizePercent?.toString() ?? ""}
                onChange={({ detail }) => {
                  if (!currentLabelRule) return;
                  const value = detail.value;
                  const parsedValue = value === "" ? NaN : parseFloat(value);
                  const finalMinImageSizePercent = isNaN(parsedValue)
                    ? defaultLabelRule.minImageSizePercent
                    : parsedValue;
                  setCurrentLabelRule({
                    ...currentLabelRule,
                    minImageSizePercent: finalMinImageSizePercent,
                  });
                }}
              />
            </FormField>
          </Form>
        )}
      </Modal>

      {/* Test Label Rules Modal */}
      <Modal
        visible={testModalVisible}
        onDismiss={() => setTestModalVisible(false)}
        header="Test Image Labels"
        size="large"
      >
        <TestLabelRules rules={labelFilteringRules} />
        <Box float="right" margin={{ top: "l" }}>
          <Button onClick={() => setTestModalVisible(false)}>Close</Button>
        </Box>
      </Modal>

      {/* Delete Label Confirmation Modal */}
      <DeleteConfirmationModal
        visible={labelDeleteConfirmationVisible}
        itemCount={selectedLabelItems.length}
        itemType="label filtering rule"
        onDismiss={() => setLabelDeleteConfirmationVisible(false)}
        onDelete={() => handleDeleteLabelRules(selectedLabelItems)}
      />
    </>
  );
};

interface TestLabelRulesProps {
  rules: LabelFilteringRule[];
}

const TestLabelRules: React.FC<TestLabelRulesProps> = ({ rules }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<TestLabelFilteringRuleLabel[] | null>(
    null
  );
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [imageModalVisible, setImageModalVisible] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loadingImage, setLoadingImage] = useState(false);

  const generateUrlsMutation = useGenerateUploadPresignedUrls();
  const generateDownloadUrlsMutation = useGenerateDownloadPresignedUrls();
  const testLabelRulesMutation = useTestLabelRules();

  const handleFileChange = (event: { detail: { value: File[] } }) => {
    setSelectedFiles(event.detail.value);
    setError(null);
    setResults(null);
  };

  const handleSubmit = async () => {
    if (selectedFiles.length === 0) {
      setError("Please select at least one image file");
      return;
    }

    if (rules.length === 0) {
      setError("There are no label rules to test");
      return;
    }

    setIsLoading(true);
    setError(null);
    setUploadProgress(0);

    try {
      // Step 1: Generate upload URLs
      const filenames = selectedFiles.map((file) => file.name);
      const uploadUrlsResponse = await generateUrlsMutation.mutateAsync(
        filenames
      );

      if (!uploadUrlsResponse || !uploadUrlsResponse.urls) {
        throw new Error("Failed to generate upload URLs");
      }

      // Step 2: Upload files
      const uploadPromises = selectedFiles.map((file, index) => {
        const uploadUrl = uploadUrlsResponse.urls?.[index];

        if (!uploadUrl?.presignedUrl || !uploadUrl.s3Key) {
          throw new Error(`Missing upload URL for file ${file.name}`);
        }

        return fetch(uploadUrl.presignedUrl, {
          method: "PUT",
          body: file,
          headers: {
            "Content-Type": file.type,
          },
        }).then(() => uploadUrl.s3Key);
      });

      const uploadedS3Keys = await Promise.all(uploadPromises);
      const filteredS3Keys = uploadedS3Keys.filter(Boolean) as string[];
      setUploadProgress(100);

      // Step 3: Test the rules
      const testResponse = await testLabelRulesMutation.mutateAsync({
        imageS3Keys: filteredS3Keys,
      });

      setResults(testResponse?.labels || []);
    } catch (err) {
      setError(
        `Error: ${
          err instanceof Error ? err.message : "Unknown error occurred"
        }`
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SpaceBetween direction="vertical" size="l">
      {error && (
        <Alert type="error" header="Error">
          {error}
        </Alert>
      )}

      <FormField
        label="Upload images to test"
        description="Select one or more images to get labels for"
      >
        <SpaceBetween direction="horizontal" size="m">
          <FileUpload
            onChange={handleFileChange}
            value={selectedFiles}
            accept="image/*"
            multiple
            constraintText="Only image files are supported"
            i18nStrings={{
              uploadButtonText: (multiple: boolean) =>
                multiple ? "Choose files" : "Choose files",
              removeFileAriaLabel: (fileIndex: number) =>
                `Remove file ${fileIndex + 1}`,
            }}
          />
          <Button onClick={() => setSelectedFiles([])}>Remove All Files</Button>
        </SpaceBetween>
      </FormField>

      {uploadProgress > 0 && uploadProgress < 100 && (
        <ProgressBar
          value={uploadProgress}
          label="Uploading files"
          description={`${uploadProgress}% complete`}
          variant="standalone"
        />
      )}

      <Box margin={{ top: "m" }}>
        <SpaceBetween direction="horizontal" size="xs">
          <Button
            onClick={handleSubmit}
            loading={isLoading}
            disabled={selectedFiles.length === 0}
          >
            Get Image Labels
          </Button>
        </SpaceBetween>
      </Box>

      {results && results.length > 0 && (
        <Table
          stripedRows
          items={results}
          columnDefinitions={[
            {
              id: "fileName",
              header: "Image",
              cell: (item) => (
                <Link
                  href="#"
                  onFollow={async (e) => {
                    e.preventDefault();
                    const s3Key = item.s3Key;
                    if (!s3Key) return;

                    setSelectedImage(s3Key);
                    setImageModalVisible(true);
                    setLoadingImage(true);

                    try {
                      const urls =
                        await generateDownloadUrlsMutation.mutateAsync([s3Key]);
                      if (urls && urls.length > 0 && urls[0]) {
                        setImageUrl(urls[0]);
                      } else {
                        console.error("Invalid or empty response:", urls);
                      }
                    } catch (error) {
                      console.error("Failed to generate download URL:", error);
                    } finally {
                      setLoadingImage(false);
                    }
                  }}
                >
                  {item.s3Key || "-"}
                </Link>
              ),
            },
            {
              id: "labels",
              header: "Detected Labels",
              cell: (item) => item.name,
            },
            {
              id: "confidence",
              header: "Confidence",
              cell: (item) =>
                (item.confidence * 100).toFixed(2).toString() + "%",
            },
          ]}
        />
      )}

      {/* Image Modal */}
      <Modal
        visible={imageModalVisible}
        onDismiss={() => setImageModalVisible(false)}
        header="Image Preview"
        size="large"
        footer={
          <Box float="right">
            <Button onClick={() => setImageModalVisible(false)}>Close</Button>
          </Box>
        }
      >
        <Box padding="l" textAlign="center">
          {loadingImage && (
            <Box padding="l">
              <ProgressBar
                label="Loading image"
                ariaLabel="Loading image"
                variant="flash"
              />
            </Box>
          )}
          {!loadingImage && selectedImage && imageUrl && (
            <img
              src={imageUrl}
              alt="Full size preview"
              style={{ maxWidth: "100%", maxHeight: "calc(80vh - 100px)" }}
            />
          )}
          {!loadingImage && (!selectedImage || !imageUrl) && (
            <Box>
              {selectedImage ? "Failed to load image" : "No image selected"}
            </Box>
          )}
        </Box>
      </Modal>
    </SpaceBetween>
  );
};
