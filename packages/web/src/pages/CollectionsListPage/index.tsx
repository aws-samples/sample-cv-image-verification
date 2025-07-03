import {
  Box,
  Button,
  Modal, // Added Modal import
  SpaceBetween,
  Table,
  TableProps,
} from "@cloudscape-design/components";
import { useState } from "react";
import { Collection } from "@aws-samples/cv-verification-api-client/src";
import { useAppLayoutContext } from "../../App";
import { useEffect } from "react";
import {
  useDeleteCollection,
  useGetAllCollections,
} from "../../hooks/Collections";

export const CollectionListPage: React.FC = () => {
  const appLayout = useAppLayoutContext();
  const { data: collections, isLoading } = useGetAllCollections();
  const [selectedCollection, setSelectedCollection] =
    useState<Collection | null>(null);
  const [isDeleteModalVisible, setIsDeleteModalVisible] = useState(false); // Added state for modal visibility
  const { mutate: deleteCollection } = useDeleteCollection();

  useEffect(() => {
    appLayout.setAppLayoutProps({
      breadcrumbs: (
        <>
          <Box display="inline">/ Collections</Box>
        </>
      ),
    });
  }, []);

  const columnDefs: TableProps.ColumnDefinition<Collection>[] = [
    {
      id: "description",
      header: "Description",
      cell: (item) => (
        <Button variant="link" href={`/collection/${item.id}`}>
          {item.description || "N/A"}
        </Button>
      ),
      sortingField: "description",
    },

    {
      id: "address",
      header: "Address",
      cell: (item) => item.address || "N/A",
      sortingField: "address",
    },
    {
      id: "files",
      header: "Files",
      cell: (item) => item.files?.length || 0,
    },
    {
      id: "items",
      header: "Items",
      cell: (item) => item.items?.length || 0,
    },
    {
      id: "createdAt",
      header: "Created At",
      cell: (item) => new Date(item.createdAt * 1000).toLocaleString(),
      sortingField: "createdAt",
    },
  ];

  // Opens the confirmation modal
  const handleDelete = () => {
    if (selectedCollection) {
      setIsDeleteModalVisible(true);
    }
  };

  // Performs the deletion after confirmation
  const confirmDelete = () => {
    if (selectedCollection) {
      deleteCollection(selectedCollection.id, {
        onSuccess: () => {
          setSelectedCollection(null);
          setIsDeleteModalVisible(false); // Close modal on success
        },
        onError: () => {
          setIsDeleteModalVisible(false); // Close modal on error too
        },
      });
    }
  };

  return (
    <SpaceBetween size="m" direction="vertical">
      <div style={{ display: "flex", justifyContent: "right" }}>
        <Box textAlign="right">
          <SpaceBetween size="m" direction="horizontal">
            <Button variant="primary" href="/collection/new">
              New Collection
            </Button>
            <Button
              onClick={handleDelete}
              variant="normal"
              disabled={!selectedCollection}
            >
              Delete Collection
            </Button>
          </SpaceBetween>
        </Box>
      </div>
      <Table
        loading={isLoading}
        loadingText="Loading collections"
        selectionType="single"
        selectedItems={selectedCollection ? [selectedCollection] : []}
        onSelectionChange={(e) => {
          if (
            e.detail.selectedItems === undefined ||
            e.detail.selectedItems.length === 0
          ) {
            setSelectedCollection(null);
            return;
          }
          setSelectedCollection(e.detail.selectedItems[0]);
        }}
        columnDefinitions={columnDefs}
        items={collections ?? []}
        trackBy="id"
        variant="container"
        header={
          <Box padding={{ vertical: "xs" }}>
            <h2>Collections</h2>
          </Box>
        }
        sortingDescending={false}
        sortingColumn={{ sortingField: "createdAt" }}
      />
      {/* Confirmation Modal */}
      <Modal
        visible={isDeleteModalVisible}
        header="Delete Collection"
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
        onDismiss={() => setIsDeleteModalVisible(false)}
      >
        {selectedCollection
          ? `Are you sure you want to delete collection ${selectedCollection.id}? This action cannot be undone.`
          : "No collection selected."}
      </Modal>
    </SpaceBetween>
  );
};
