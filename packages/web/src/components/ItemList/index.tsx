import {
  Alert,
  Box,
  Button,
  Modal, // Added Modal
  SpaceBetween,
  Spinner,
  Table,
  TableProps,
} from "@cloudscape-design/components";
import { useState } from "react";
import { useDeleteItem, useGetAllItems } from "../../hooks/Items";
import { Item } from "@aws-samples/cv-verification-api-client/src";

export const ItemList: React.FC = () => {
  const {
    data: items,
    refetch: refetchItems,
    isPending: isFetchingItems,
  } = useGetAllItems(); // Added refetch
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [isDeleteModalVisible, setIsDeleteModalVisible] = useState(false); // Added modal state
  const { mutate: deleteItem } = useDeleteItem();
  const columnDefs: TableProps.ColumnDefinition<Item>[] = [
    {
      header: "Name",
      cell: (item) => (
        <Button variant="link" href={"/itemdetail/" + item.id}>
          {item.name}
        </Button>
      ),
    },
    {
      header: "Cluster Number",
      cell: (item) => item.clusterNumber ?? "",
    },
    {
      header: "Description",
      cell: (item) => item.description,
    },
    {
      header: "Rules",
      cell: (item) =>
        (item.labelFilteringRules ?? []).length +
        (item.descriptionFilteringRules ?? []).length,
    },
  ];

  // Renamed from handleDelete and updated logic
  const confirmDelete = () => {
    if (selectedItem) {
      deleteItem(selectedItem.id, {
        onSuccess: () => {
          setSelectedItem(null);
          setIsDeleteModalVisible(false); // Close modal on success
          refetchItems();
        },
        onError: () => {
          // Optionally handle error, e.g., show a notification
          setIsDeleteModalVisible(false); // Close modal even on error
        },
      });
    }
  };

  return (
    <SpaceBetween size="m" direction="vertical">
      <div style={{ display: "flex", justifyContent: "right" }}>
        <Box textAlign="right">
          <SpaceBetween size="m" direction="horizontal">
            <Button variant="primary" href="/newitem">
              New Item
            </Button>
            <Button
              onClick={() => setIsDeleteModalVisible(true)} // Open modal on click
              variant="normal"
              disabled={!selectedItem}
            >
              Delete Item
            </Button>
          </SpaceBetween>
        </Box>
      </div>
      <Table
        selectionType="single"
        selectedItems={selectedItem ? [selectedItem] : undefined}
        onSelectionChange={(e) => {
          if (
            e.detail.selectedItems === undefined ||
            e.detail.selectedItems.length === 0
          ) {
            setSelectedItem(null);
            return;
          }
          setSelectedItem(e.detail.selectedItems[0]);
        }}
        loading={isFetchingItems}
        loadingText="Loading Items"
        columnDefinitions={columnDefs}
        items={items ?? []}
        stripedRows
      ></Table>

      {/* Delete Confirmation Modal */}
      <Modal
        onDismiss={() => setIsDeleteModalVisible(false)}
        visible={isDeleteModalVisible}
        closeAriaLabel="Close modal"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="link"
                onClick={() => setIsDeleteModalVisible(false)}
              >
                Cancel
              </Button>
              <Button variant="primary" onClick={confirmDelete}>
                Delete
              </Button>
            </SpaceBetween>
          </Box>
        }
        header="Delete Item"
      >
        Are you sure you want to delete the item "{selectedItem?.name}"? This
        action cannot be undone.
      </Modal>
    </SpaceBetween>
  );
};
