import {
  Box,
  Button,
  Modal,
  SpaceBetween,
  Table,
  TableProps,
} from "@cloudscape-design/components";
import { useState, useEffect } from "react";
import { useAppLayoutContext } from "../../App";
import { useDeleteAgent, useGetAllAgents } from "../../hooks/Agents";
import { Agent } from "@aws-samples/cv-verification-api-client/src/models/Agent";
import { AgentTypes } from "@aws-samples/cv-verification-api-client/src";

export const AgentListPage: React.FC = () => {
  const appLayout = useAppLayoutContext();
  const { data: agents, isLoading } = useGetAllAgents();
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isDeleteModalVisible, setIsDeleteModalVisible] = useState(false);
  const { mutate: deleteAgent } = useDeleteAgent();

  useEffect(() => {
    appLayout.setAppLayoutProps({
      breadcrumbs: (
        <>
          / <Box display="inline">Agents</Box>
        </>
      ),
    });
  }, []);

  const getAgentType = (agent: Agent) => {
    if ("knowledgeBaseId" in agent) {
      return "Knowledge Base";
    } else if ("apiEndpoint" in agent) {
      return "REST API";
    } else if ("athena" in agent) {
      return "Amazon Athena";
    }
    return "Unknown";
  };

  const getAgentTypeSpecificInfo = (agent: Agent) => {
    if (agent.type === AgentTypes.KnowledgeBase)
      return "Knowledge Base ID: " + (agent.knowledgeBaseId || "N/A");
    if (agent.type === AgentTypes.RestApi)
      return "API Endpoint: " + (agent.apiEndpoint || "N/A");
    if (agent.type === AgentTypes.AmazonAthena)
      return "Athena Database: " + (agent.athenaDatabase || "N/A");
    return "N/A";
  };

  const columnDefs: TableProps.ColumnDefinition<Agent>[] = [
    {
      id: "name",
      header: "Name",
      cell: (item) => (
        <Button variant="link" href={`/agent/${item.id}`}>
          {item.name}
        </Button>
      ),
      sortingField: "name",
    },
    {
      id: "description",
      header: "Description",
      cell: (item) => item.description || "N/A",
      sortingField: "description",
    },
    {
      id: "type",
      header: "Type",
      cell: (item) => getAgentType(item),
    },
    {
      id: "typeInfo",
      header: "Configuration",
      cell: (item) => getAgentTypeSpecificInfo(item),
    },
    {
      id: "createdAt",
      header: "Created At",
      cell: (item) => new Date(item.createdAt * 1000).toLocaleString(),
      sortingField: "createdAt",
    },
  ];

  const handleDelete = () => {
    if (selectedAgent) {
      setIsDeleteModalVisible(true);
    }
  };

  const confirmDelete = () => {
    if (selectedAgent) {
      deleteAgent(selectedAgent.id, {
        onSuccess: () => {
          setSelectedAgent(null);
          setIsDeleteModalVisible(false);
        },
        onError: () => {
          setIsDeleteModalVisible(false);
        },
      });
    }
  };

  return (
    <SpaceBetween size="m" direction="vertical">
      <div style={{ display: "flex", justifyContent: "right" }}>
        <Box textAlign="right">
          <SpaceBetween size="m" direction="horizontal">
            <Button variant="primary" href="/agent/new">
              New Agent
            </Button>
            <Button
              onClick={handleDelete}
              variant="normal"
              disabled={!selectedAgent}
            >
              Delete Agent
            </Button>
          </SpaceBetween>
        </Box>
      </div>
      <Table
        loading={isLoading}
        loadingText="Loading agents"
        selectionType="single"
        selectedItems={selectedAgent ? [selectedAgent] : []}
        onSelectionChange={(e) => {
          if (
            e.detail.selectedItems === undefined ||
            e.detail.selectedItems.length === 0
          ) {
            setSelectedAgent(null);
            return;
          }
          setSelectedAgent(e.detail.selectedItems[0]);
        }}
        columnDefinitions={columnDefs}
        items={agents ?? []}
        trackBy="id"
        variant="container"
        header={
          <Box padding={{ vertical: "xs" }}>
            <h2>Agents</h2>
          </Box>
        }
        sortingDescending={false}
        sortingColumn={{ sortingField: "createdAt" }}
      />
      <Modal
        visible={isDeleteModalVisible}
        header="Delete Agent"
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
        {selectedAgent
          ? `Are you sure you want to delete agent "${selectedAgent.name}"? This action cannot be undone.`
          : "No agent selected."}
      </Modal>
    </SpaceBetween>
  );
};
