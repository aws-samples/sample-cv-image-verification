import React, { useState, useEffect } from "react";
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
  Textarea,
  Checkbox,
  FlashbarProps, // Keep type for state
} from "@cloudscape-design/components";
import { v4 as uuidv4 } from "uuid";
import { DeleteConfirmationModal } from "./DeleteConfirmationModal";
import { DescriptionDetailModal } from "./DescriptionDetailModal"; // Import the new modal
import { DescriptionFilteringRule } from "@aws-samples/cv-verification-api-client/src";
import { defaultDescriptionRule, DescriptionFormErrors } from "./types";
import { useUpdateItem } from "../../hooks/Items";

interface DescriptionRulesSectionProps {
  itemId: string;
  rules: DescriptionFilteringRule[];
  onRulesChange: (updatedRules: DescriptionFilteringRule[]) => void;
  selectedAgentIds?: string[]; // Optional prop for selected agent IDs
}

export const DescriptionRulesSection: React.FC<
  DescriptionRulesSectionProps
> = ({ itemId, rules: initialRules, onRulesChange, selectedAgentIds }) => {
  const [descriptionFilteringRules, setDescriptionFilteringRules] = useState<
    DescriptionFilteringRule[]
  >([]);

  // Description Rule State
  const [descriptionModalVisible, setDescriptionModalVisible] = useState(false);
  const [isDescriptionEditMode, setIsDescriptionEditMode] = useState(false);
  const [currentDescriptionRule, setCurrentDescriptionRule] =
    useState<DescriptionFilteringRule | null>(null);
  const [descriptionCurrentPage, setDescriptionCurrentPage] = useState(1);
  const [descriptionFilterText, setDescriptionFilterText] = useState("");
  const [descriptionFormErrors, setDescriptionFormErrors] =
    useState<DescriptionFormErrors>({});
  const [selectedDescriptionItems, setSelectedDescriptionItems] = useState<
    DescriptionFilteringRule[]
  >([]);
  const [
    descriptionDeleteConfirmationVisible,
    setDescriptionDeleteConfirmationVisible,
  ] = useState(false);
  // State for description detail modal
  const [descriptionDetailModalVisible, setDescriptionDetailModalVisible] =
    useState(false);
  // Store the whole rule being viewed/edited in the detail modal
  const [ruleBeingViewed, setRuleBeingViewed] =
    useState<DescriptionFilteringRule | null>(null);
  // State for flash messages
  const [flashItems, setFlashItems] = useState<
    FlashbarProps.MessageDefinition[]
  >([]);

  // Use the mutation hook
  const updateItemMutation = useUpdateItem(itemId);

  const pageSize = 5;

  // Effect to update state when props change
  useEffect(() => {
    setDescriptionFilteringRules(initialRules);
  }, [initialRules]);

  // --- Description Rule Logic ---

  const filteredDescriptionRules = descriptionFilteringRules.filter((rule) => {
    if (!descriptionFilterText) return true;
    const searchText = descriptionFilterText.toLowerCase();
    return (
      rule.description.toLowerCase().includes(searchText) ||
      (rule.minConfidence?.toString() ?? "").includes(searchText) ||
      (rule.mandatory ? "yes" : "no").includes(searchText) // Search mandatory field
    );
  });

  const totalDescriptionPages = Math.ceil(
    filteredDescriptionRules.length / pageSize
  );
  const descriptionStartIndex = (descriptionCurrentPage - 1) * pageSize;
  const visibleDescriptionRules = filteredDescriptionRules.slice(
    descriptionStartIndex,
    descriptionStartIndex + pageSize
  );

  const handleCreateDescriptionRule = () => {
    setCurrentDescriptionRule({
      ...defaultDescriptionRule,
      id: "", // Temporary ID
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
    setIsDescriptionEditMode(false);
    setDescriptionFormErrors({});
    setDescriptionModalVisible(true);
  };

  const handleEditDescriptionRule = (rule: DescriptionFilteringRule) => {
    setCurrentDescriptionRule({ ...rule });
    setIsDescriptionEditMode(true);
    setDescriptionFormErrors({});
    setDescriptionModalVisible(true);
  };

  const handleDeleteDescriptionRules = (
    rulesToDelete: DescriptionFilteringRule[]
  ) => {
    const updatedRules = descriptionFilteringRules.filter(
      (rule) => !rulesToDelete.some((deleteRule) => deleteRule.id === rule.id)
    );
    setDescriptionFilteringRules(updatedRules);
    setSelectedDescriptionItems([]);
    setDescriptionDeleteConfirmationVisible(false);

    if (
      descriptionCurrentPage > 1 &&
      updatedRules.length <= (descriptionCurrentPage - 1) * pageSize
    ) {
      setDescriptionCurrentPage(descriptionCurrentPage - 1);
    }

    onRulesChange(updatedRules); // Notify parent
  };

  const validateDescriptionForm = (): boolean => {
    const errors: DescriptionFormErrors = {};
    if (!currentDescriptionRule) return false;

    if (!currentDescriptionRule.description.trim()) {
      errors.description = "Description is required";
    }

    const confidence = currentDescriptionRule.minConfidence;
    if (
      confidence === undefined ||
      confidence === null ||
      isNaN(confidence) ||
      confidence < 0 ||
      confidence > 1
    ) {
      errors.minConfidence = "Confidence must be a number between 0 and 1";
    }

    setDescriptionFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveDescriptionRule = () => {
    if (!validateDescriptionForm() || !currentDescriptionRule) return;

    let updatedRules: DescriptionFilteringRule[];
    if (isDescriptionEditMode) {
      updatedRules = descriptionFilteringRules.map((rule) =>
        rule.id === currentDescriptionRule.id
          ? {
              ...currentDescriptionRule,
              createdAt: currentDescriptionRule.createdAt ?? Date.now(),
              updatedAt: Date.now(),
            }
          : rule
      );
    } else {
      const newRule: DescriptionFilteringRule = {
        ...currentDescriptionRule,
        id: uuidv4(),
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      updatedRules = [...descriptionFilteringRules, newRule];
    }

    setDescriptionFilteringRules(updatedRules);
    setDescriptionModalVisible(false);
    onRulesChange(updatedRules); // Notify parent
  };

  // Handler for saving description changes from the detail modal
  const handleSaveDescriptionFromModal = (newDescription: string) => {
    if (!ruleBeingViewed) return;

    const updatedRules = descriptionFilteringRules.map((rule) =>
      rule.id === ruleBeingViewed.id
        ? { ...rule, description: newDescription, updatedAt: Date.now() }
        : rule
    );

    // Call the mutation instead of onRulesChange directly for this specific save action
    updateItemMutation.mutate(
      { descriptionFilteringRules: updatedRules }, // Pass only the changed rules type if API supports partial updates, otherwise pass all rules
      {
        onSuccess: () => {
          // Update local state on success
          setDescriptionFilteringRules(updatedRules);
          // Notify parent component of the changes
          onRulesChange(updatedRules);
          // Add success flash message
          const messageId = uuidv4();
          setFlashItems([
            {
              type: "success",
              content: "Description saved successfully.",
              dismissible: true,
              id: messageId,
              onDismiss: () =>
                setFlashItems((items) =>
                  items.filter((item) => item.id !== messageId)
                ), // Correct inline dismiss
            },
          ]);
          // Keep modal open and rule selected
        },
        onError: (error) => {
          // Add error flash message
          const messageId = uuidv4();
          setFlashItems([
            {
              type: "error",
              content: `Failed to save description: ${
                error instanceof Error ? error.message : String(error)
              }`,
              dismissible: true,
              id: messageId,
              onDismiss: () =>
                setFlashItems((items) =>
                  items.filter((item) => item.id !== messageId)
                ), // Correct inline dismiss
            },
          ]);
        },
      }
    );
  };

  // Removed handleDismissFlashItem as it's handled inline now

  const handleDescriptionActionsClick = ({
    detail,
  }: {
    detail: { id: string };
  }) => {
    switch (detail.id) {
      case "edit":
        if (selectedDescriptionItems.length === 1) {
          handleEditDescriptionRule(selectedDescriptionItems[0]);
        }
        break;
      case "delete":
        if (selectedDescriptionItems.length > 0) {
          setDescriptionDeleteConfirmationVisible(true);
        }
        break;
    }
  };

  return (
    <>
      <Table
        stripedRows
        resizableColumns
        header={
          <Header
            counter={`(${descriptionFilteringRules.length})`}
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <ButtonDropdown
                  items={[
                    {
                      id: "edit",
                      text: "Edit",
                      disabled: selectedDescriptionItems.length !== 1,
                    },
                    {
                      id: "delete",
                      text: "Delete",
                      disabled: selectedDescriptionItems.length === 0,
                    },
                  ]}
                  onItemClick={handleDescriptionActionsClick}
                  disabled={selectedDescriptionItems.length === 0}
                >
                  Actions
                </ButtonDropdown>
                <Button variant="primary" onClick={handleCreateDescriptionRule}>
                  Create description rule
                </Button>
              </SpaceBetween>
            }
          >
            Description Filtering Rules
          </Header>
        }
        columnDefinitions={[
          {
            id: "description",
            header: "Description",
            cell: (item: DescriptionFilteringRule) => (
              <p
                onClick={() => {
                  setRuleBeingViewed(item); // Set the rule object
                  setDescriptionDetailModalVisible(true);
                }}
                title={item.description}
                style={{ cursor: "pointer", textDecoration: "underline" }}
              >
                {item.description.length > 100
                  ? `${item.description.substring(0, 100)}...`
                  : item.description}
              </p>
            ),
            sortingField: "description",
          },
          {
            id: "minConfidence",
            header: "Min Confidence",
            cell: (item: DescriptionFilteringRule) =>
              item.minConfidence !== undefined && item.minConfidence !== null
                ? item.minConfidence.toFixed(2)
                : "N/A",
            sortingField: "minConfidence",
          },
          {
            id: "mandatory",
            header: "Mandatory",
            cell: (item: DescriptionFilteringRule) =>
              item.mandatory ? "Yes" : "No",
            sortingField: "mandatory",
          },
          {
            id: "createdAt",
            header: "Created",
            cell: (item: DescriptionFilteringRule) =>
              item.createdAt
                ? new Date(item.createdAt).toLocaleString()
                : "N/A",
            sortingField: "createdAt",
          },
          {
            id: "updatedAt",
            header: "Updated",
            cell: (item: DescriptionFilteringRule) =>
              item.updatedAt
                ? new Date(item.updatedAt).toLocaleString()
                : "N/A",
            sortingField: "updatedAt",
          },
        ]}
        items={visibleDescriptionRules}
        selectionType="multi"
        selectedItems={selectedDescriptionItems}
        onSelectionChange={({ detail }) =>
          setSelectedDescriptionItems(detail.selectedItems)
        }
        pagination={
          <Pagination
            currentPageIndex={descriptionCurrentPage}
            pagesCount={totalDescriptionPages}
            onChange={({ detail }) =>
              setDescriptionCurrentPage(detail.currentPageIndex)
            }
          />
        }
        filter={
          <TextFilter
            filteringText={descriptionFilterText}
            onChange={({ detail }) =>
              setDescriptionFilterText(detail.filteringText)
            }
            filteringPlaceholder="Find description rules"
            countText={`${filteredDescriptionRules.length} matches`}
          />
        }
        empty={
          <Box textAlign="center" color="inherit">
            <b>No description filtering rules</b>
            <Box padding={{ bottom: "s" }} variant="p" color="inherit">
              No description filtering rules have been defined yet.
            </Box>
            <Button onClick={handleCreateDescriptionRule}>
              Create description rule
            </Button>
          </Box>
        }
      />

      {/* Create/Edit Description Rule Modal */}
      <Modal
        visible={descriptionModalVisible}
        onDismiss={() => setDescriptionModalVisible(false)}
        header={
          isDescriptionEditMode
            ? "Edit description rule"
            : "Create description rule"
        }
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="link"
                onClick={() => setDescriptionModalVisible(false)}
              >
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveDescriptionRule}>
                {isDescriptionEditMode ? "Save changes" : "Create rule"}
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        {currentDescriptionRule && (
          <Form>
            <FormField
              label="Description"
              description="Text description to filter on. Describe in natural language what is expected in the image."
              errorText={descriptionFormErrors.description}
            >
              <Textarea
                rows={10}
                value={currentDescriptionRule.description}
                onChange={({ detail }) => {
                  if (!currentDescriptionRule) return;
                  setCurrentDescriptionRule({
                    ...currentDescriptionRule,
                    description: detail.value,
                  });
                }}
              ></Textarea>
            </FormField>
            <FormField
              label="Minimum Confidence"
              description="Threshold for description confidence (0.0 to 1.0)"
              errorText={descriptionFormErrors.minConfidence}
            >
              <Input
                type="number"
                step={0.01}
                value={currentDescriptionRule.minConfidence?.toString() ?? ""}
                onChange={({ detail }) => {
                  if (!currentDescriptionRule) return;
                  const value = detail.value;
                  const parsedValue = value === "" ? NaN : parseFloat(value);
                  const finalMinConfidence = isNaN(parsedValue)
                    ? defaultDescriptionRule.minConfidence
                    : parsedValue;
                  setCurrentDescriptionRule({
                    ...currentDescriptionRule,
                    minConfidence: finalMinConfidence,
                  });
                }}
              />
            </FormField>
            <FormField>
              <Checkbox
                checked={currentDescriptionRule?.mandatory ?? false}
                onChange={({ detail }) => {
                  if (!currentDescriptionRule) return;
                  setCurrentDescriptionRule({
                    ...currentDescriptionRule,
                    mandatory: detail.checked,
                  });
                }}
              >
                Mandatory Rule
              </Checkbox>
            </FormField>
          </Form>
        )}
      </Modal>

      {/* Delete Description Confirmation Modal */}
      <DeleteConfirmationModal
        visible={descriptionDeleteConfirmationVisible}
        itemCount={selectedDescriptionItems.length}
        itemType="description filtering rule"
        onDismiss={() => setDescriptionDeleteConfirmationVisible(false)}
        onDelete={() => handleDeleteDescriptionRules(selectedDescriptionItems)}
      />

      {/* Description Detail Modal */}
      {ruleBeingViewed && ( // Render modal only when a rule is selected
        <DescriptionDetailModal
          selectedAgentIds={selectedAgentIds}
          visible={descriptionDetailModalVisible}
          description={ruleBeingViewed.description}
          onDismiss={() => {
            setDescriptionDetailModalVisible(false);
            setRuleBeingViewed(null);
            setFlashItems([]); // Clear flash messages on dismiss
          }}
          onSave={handleSaveDescriptionFromModal}
          isSaving={updateItemMutation.isPending}
          flashItems={flashItems}
          // Removed onDismissFlashItem prop
        />
      )}
    </>
  );
};
