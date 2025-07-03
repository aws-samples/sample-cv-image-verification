import React from "react";
import {
  Modal,
  Box,
  SpaceBetween,
  Button,
  Alert,
} from "@cloudscape-design/components";

interface DeleteConfirmationModalProps {
  visible: boolean;
  itemCount: number;
  itemType: string; // e.g., "label filtering rule", "description filtering rule"
  onDismiss: () => void;
  onDelete: () => void;
}

export const DeleteConfirmationModal: React.FC<
  DeleteConfirmationModalProps
> = ({ visible, itemCount, itemType, onDismiss, onDelete }) => {
  if (itemCount === 0) {
    return null; // Don't render if no items are selected
  }

  return (
    <Modal
      visible={visible}
      onDismiss={onDismiss}
      header={`Delete ${itemType}${itemCount > 1 ? "s" : ""}`}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onDismiss}>
              Cancel
            </Button>
            <Button variant="primary" onClick={onDelete}>
              Delete
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <Alert type="warning" header="Delete confirmation">
        Are you sure you want to delete {itemCount} {itemType}
        {itemCount > 1 ? "s" : ""}? This action cannot be undone.
      </Alert>
    </Modal>
  );
};
