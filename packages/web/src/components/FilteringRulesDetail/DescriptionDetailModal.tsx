import React from "react";
import {
  Modal,
  Box,
  Button,
  SpaceBetween,
  Textarea, // Import Textarea
  Flashbar, // Import Flashbar
  FlashbarProps, // Import FlashbarProps
} from "@cloudscape-design/components";
import { DescriptionDetailTester } from "./DescriptionDetailTester";
import { useState, useEffect } from "react"; // Import useState, useEffect

interface DescriptionDetailModalProps {
  visible: boolean;
  description: string;
  onDismiss: () => void;
  onSave: (newDescription: string) => void;
  isSaving?: boolean;
  flashItems?: FlashbarProps.MessageDefinition[];
  selectedAgentIds?: string[]; // Optional prop for selected agent IDs
  // Removed onDismissFlashItem prop
}

export const DescriptionDetailModal: React.FC<DescriptionDetailModalProps> = ({
  visible,
  description,
  onDismiss,
  onSave,
  isSaving = false,
  flashItems = [],
  selectedAgentIds = [],
  // Removed onDismissFlashItem from destructuring
}) => {
  const [editableDescription, setEditableDescription] = useState(description);

  // Reset editable description when the modal is opened with a new description prop
  useEffect(() => {
    if (visible) {
      setEditableDescription(description);
    }
  }, [description, visible]);

  const handleSave = () => {
    onSave(editableDescription);
    // Optionally keep modal open or close based on parent logic after save
    // onDismiss(); // Example: close after save attempt
  };

  const hasChanged = editableDescription !== description;

  return (
    <Modal
      visible={visible}
      onDismiss={onDismiss}
      header="Edit Rule Description" // Update header
      size="large"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onDismiss} disabled={isSaving}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSave}
              disabled={!hasChanged || isSaving} // Disable if no changes or saving
              loading={isSaving} // Show loading indicator
            >
              Save
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      {/* Render Flashbar without onDismiss prop */}
      <Flashbar items={flashItems} />
      <SpaceBetween size="m">
        {/* Replace Box with Textarea */}
        <Textarea
          value={editableDescription}
          onChange={({ detail }) => setEditableDescription(detail.value)}
          rows={10} // Adjust rows as needed
          disabled={isSaving}
        />
        {/* Pass the editableDescription to the tester */}
        <DescriptionDetailTester
          selectedAgentIds={selectedAgentIds}
          description={editableDescription}
        />
      </SpaceBetween>
    </Modal>
  );
};
