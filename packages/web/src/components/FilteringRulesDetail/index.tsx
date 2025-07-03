import React, { useState, useEffect } from "react";
import {
  SpaceBetween,
  AppLayout,
  HelpPanel,
  Spinner, // Import Spinner for loading state
  Alert, // Import Alert for error state
} from "@cloudscape-design/components";

import { LabelRulesSection } from "./LabelRulesSection";
import { DescriptionRulesSection } from "./DescriptionRulesSection";
import {
  DescriptionFilteringRule,
  LabelFilteringRule,
} from "@aws-samples/cv-verification-api-client/src";
import { useGetAllItems, useUpdateItem } from "../../hooks/Items";

export interface FilteringRulesDetailProps {
  itemId: string;
  labelRules: LabelFilteringRule[];
  descriptionRules: DescriptionFilteringRule[];
  onRulesChange?: (rules: {
    labelRules: LabelFilteringRule[];
    descriptionRules: DescriptionFilteringRule[];
  }) => void;
  onSaveSuccess?: () => void;
  onSaveError?: (error: unknown) => void;
  selectedAgentIds?: string[]; // Optional prop for selected agent IDs
}

export const FilteringRulesDetail: React.FC<FilteringRulesDetailProps> = ({
  itemId,
  labelRules: initialLabelRules,
  descriptionRules: initialDescriptionRules,
  onRulesChange,
  onSaveSuccess,
  onSaveError,
  selectedAgentIds,
}) => {
  const [toolsOpen, setToolsOpen] = useState(false);
  const [labelFilteringRules, setLabelFilteringRules] = useState<
    LabelFilteringRule[]
  >([]);
  const [descriptionFilteringRules, setDescriptionFilteringRules] = useState<
    DescriptionFilteringRule[]
  >([]);
  const updateItemMutation = useUpdateItem(itemId);
  const { isLoading: isLoadingItems, error: errorLoadingItems } =
    useGetAllItems(); // Correct hook name

  // --- Prop Change Effects ---
  useEffect(() => {
    setLabelFilteringRules(initialLabelRules || []);
  }, [initialLabelRules]);

  useEffect(() => {
    setDescriptionFilteringRules(initialDescriptionRules || []);
  }, [initialDescriptionRules]);

  // Handler for when LabelRulesSection reports changes
  const handleLabelRulesChange = (updatedLabelRules: LabelFilteringRule[]) => {
    setLabelFilteringRules(updatedLabelRules);
    // Trigger mutation with the latest state and callbacks
    // Ensure all rule types are included in the mutation payload
    updateItemMutation.mutate(
      {
        labelFilteringRules: updatedLabelRules,
        descriptionFilteringRules: descriptionFilteringRules,
      },
      {
        onSuccess: onSaveSuccess,
        onError: onSaveError,
      }
    );
    if (onRulesChange) {
      onRulesChange({
        labelRules: updatedLabelRules,
        descriptionRules: descriptionFilteringRules,
      });
    }
  };

  // Handler for when DescriptionRulesSection reports changes
  const handleDescriptionRulesChange = (
    updatedDescriptionRules: DescriptionFilteringRule[]
  ) => {
    setDescriptionFilteringRules(updatedDescriptionRules);
    // Trigger mutation with the latest state and callbacks
    // Ensure all rule types are included in the mutation payload
    updateItemMutation.mutate(
      {
        labelFilteringRules: labelFilteringRules,
        descriptionFilteringRules: updatedDescriptionRules,
      },
      {
        onSuccess: onSaveSuccess,
        onError: onSaveError,
      }
    );
    if (onRulesChange) {
      onRulesChange({
        labelRules: labelFilteringRules,
        descriptionRules: updatedDescriptionRules,
      });
    }
  };

  if (isLoadingItems) {
    return <Spinner size="large" />;
  }

  if (errorLoadingItems) {
    return (
      <Alert statusIconAriaLabel="Error" type="error">
        Error loading items list:{" "}
        {errorLoadingItems instanceof Error
          ? errorLoadingItems.message
          : String(errorLoadingItems)}
      </Alert>
    );
  }

  const helpPanelContent = (
    <HelpPanel header={<h2>About Filtering Rules</h2>}>
      <p>This section manages two types of filtering rules for an item:</p>
      <ol>
        <li>
          <strong>Label Filtering Rules:</strong>
          <ul>
            <li>Applied first in the image processing pipeline.</li>
            <li>
              Use object detection models to identify labels (e.g., "car",
              "person", "damaged panel").
            </li>
            <li>
              Define specific labels, minimum confidence scores, and minimum
              object size percentages.
            </li>
            <li>
              Images that <strong>match</strong> these rules are typically{" "}
              <strong>excluded</strong> (as label detection is cheap).
            </li>
            <li>Acts as a quick initial filter.</li>
          </ul>
        </li>
        <li>
          <strong>Description Filtering Rules:</strong>
          <ul>
            <li>Applied after label filtering to remaining images.</li>
            <li>
              Use more sophisticated (and expensive) LLMs or embedding models.
            </li>
            <li>
              Define a natural language description of what should{" "}
              <strong>be present</strong> (e.g., "Significant rust on car
              door").
            </li>
            <li>Include a minimum confidence score for the match.</li>
            <li>Performs a deeper, semantic analysis.</li>
          </ul>
        </li>
      </ol>
      <p>
        You can create, edit, and delete both types of rules using the tables
        below. Changes are saved automatically when rules are modified or
        deleted.
      </p>
    </HelpPanel>
  );

  const mainContent = (
    <SpaceBetween size="l">
      <LabelRulesSection
        rules={labelFilteringRules}
        onRulesChange={handleLabelRulesChange}
      />
      <DescriptionRulesSection
        selectedAgentIds={selectedAgentIds ?? []}
        rules={descriptionFilteringRules}
        onRulesChange={handleDescriptionRulesChange} // Keep for potential state sync if needed elsewhere
        itemId={itemId} // Pass the itemId to DescriptionRulesSection
      />
    </SpaceBetween>
  );

  return (
    <AppLayout
      contentType="table"
      content={mainContent} // Render mainContent directly
      tools={helpPanelContent}
      toolsOpen={toolsOpen}
      onToolsChange={({ detail }) => setToolsOpen(detail.open)}
      navigationHide={true}
    />
    // Modals are now handled within their respective section components
  );
};
