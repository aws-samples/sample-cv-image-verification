import React, { useState, useEffect } from "react";
import {
  Button,
  Container,
  Form,
  FormField,
  Header,
  Input,
  SpaceBetween,
  Textarea,
  Alert,
  Select,
} from "@cloudscape-design/components";
import {
  Agent,
  CreateAgentRequest,
  UpdateAgentRequest,
} from "@aws-samples/cv-verification-api-client/src";
import { AgentTypes } from "@aws-samples/cv-verification-api-client/src/models/AgentTypes";
import { useCreateAgent, useUpdateAgent } from "../../hooks/Agents";

interface AgentDetailsProps {
  agent?: Agent | null;
  onSave?: (agentId: string) => void;
  onCancel?: () => void;
}

const AgentDetails: React.FC<AgentDetailsProps> = ({
  agent,
  onSave,
  onCancel,
}) => {
  const isEditing = !!agent;
  const [name, setName] = useState<string>(agent?.name || "");
  const [description, setDescription] = useState<string>(
    agent?.description || ""
  );
  const [prompt, setPrompt] = useState<string>(agent?.prompt || "");
  const [agentType, setAgentType] = useState<string>(
    agent?.type || AgentTypes.KnowledgeBase
  );
  const [knowledgeBaseId, setKnowledgeBaseId] = useState<string>(
    agent?.knowledgeBaseId || ""
  );
  const [apiEndpoint, setApiEndpoint] = useState<string>(
    agent?.apiEndpoint || ""
  );
  const [athenaDatabase, setAthenaDatabase] = useState<string>(
    agent?.athenaDatabase || ""
  );
  const [athenaQuery, setAthenaQuery] = useState<string>(
    agent?.athenaQuery || ""
  );
  const [error, setError] = useState<string | null>(null);

  const { mutateAsync: createAgent, isPending: isCreating } = useCreateAgent();
  const { mutateAsync: updateAgent, isPending: isUpdating } = useUpdateAgent(
    agent?.id
  );

  const isLoading = isCreating || isUpdating;

  useEffect(() => {
    if (agent) {
      setName(agent.name || "");
      setDescription(agent.description || "");
      setPrompt(agent.prompt || "");
      setAgentType(agent.type || AgentTypes.KnowledgeBase);
      setKnowledgeBaseId(agent.knowledgeBaseId || "");
      setApiEndpoint(agent.apiEndpoint || "");
      setAthenaDatabase(agent.athenaDatabase || "");
      setAthenaQuery(agent.athenaQuery || "");
      setError(null);
    } else {
      setName("");
      setDescription("");
      setPrompt("");
      setAgentType(AgentTypes.KnowledgeBase);
      setKnowledgeBaseId("");
      setApiEndpoint("");
      setAthenaDatabase("");
      setAthenaQuery("");
      setError(null);
    }
  }, [agent]);

  const handleSubmit = async () => {
    setError(null);

    // Validation
    if (!name.trim()) {
      setError("Agent name is required");
      return;
    }
    if (!prompt.trim()) {
      setError("Agent prompt is required");
      return;
    }
    if (agentType === AgentTypes.KnowledgeBase && !knowledgeBaseId.trim()) {
      setError("Knowledge Base ID is required for Knowledge Base agents");
      return;
    }
    if (agentType === AgentTypes.RestApi && !apiEndpoint.trim()) {
      setError("API Endpoint is required for REST API agents");
      return;
    }
    if (agentType === AgentTypes.AmazonAthena && !athenaDatabase.trim()) {
      setError("Athena Database is required for Amazon Athena agents");
      return;
    }
    if (agentType === AgentTypes.AmazonAthena && !athenaQuery.trim()) {
      setError("Athena Query is required for Amazon Athena agents");
      return;
    }

    try {
      if (isEditing && agent) {
        // Update existing agent
        const updateRequest: UpdateAgentRequest = {
          name,
          description: description || undefined,
          prompt,
          type: agentType,
          knowledgeBaseId:
            agentType === AgentTypes.KnowledgeBase
              ? knowledgeBaseId
              : undefined,
          apiEndpoint:
            agentType === AgentTypes.RestApi ? apiEndpoint : undefined,
          athenaDatabase:
            agentType === AgentTypes.AmazonAthena ? athenaDatabase : null,
          athenaQuery:
            agentType === AgentTypes.AmazonAthena ? athenaQuery : null,
        };
        const response = await updateAgent(updateRequest);
        if (response && onSave) {
          onSave(agent.id);
        }
      } else {
        // Create new agent
        const createRequest: CreateAgentRequest = {
          name,
          description: description || undefined,
          prompt,
          type: agentType,
          knowledgeBaseId:
            agentType === AgentTypes.KnowledgeBase
              ? knowledgeBaseId
              : undefined,
          apiEndpoint:
            agentType === AgentTypes.RestApi ? apiEndpoint : undefined,
          athenaDatabase:
            agentType === AgentTypes.AmazonAthena ? athenaDatabase : null,
          athenaQuery:
            agentType === AgentTypes.AmazonAthena ? athenaQuery : null,
        };
        const response = await createAgent(createRequest);
        if (response && onSave && response.id) {
          onSave(response.id);
        }
      }
    } catch (err) {
      console.error("Error saving agent:", err);
      setError("Failed to save agent");
    }
  };

  const agentTypeOptions = [
    { label: "Knowledge Base Agent", value: AgentTypes.KnowledgeBase },
    { label: "REST API Agent", value: AgentTypes.RestApi },
    { label: "Amazon Athena Agent", value: AgentTypes.AmazonAthena },
  ];

  return (
    <Container>
      <SpaceBetween size="l">
        <Header variant="h2">
          {isEditing ? "Edit Agent" : "Create Agent"}
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
                {isEditing ? "Save changes" : "Create agent"}
              </Button>
            </SpaceBetween>
          }
        >
          <SpaceBetween size="l">
            <FormField
              label="Agent Name"
              description="A descriptive name for the agent"
            >
              <Input
                value={name}
                onChange={({ detail }) => setName(detail.value)}
                disabled={isLoading}
                placeholder="Enter agent name"
              />
            </FormField>

            <FormField
              label="Description"
              description="Optional description of what this agent does"
            >
              <Textarea
                value={description}
                onChange={({ detail }) => setDescription(detail.value)}
                disabled={isLoading}
                placeholder="Enter agent description"
                rows={2}
              />
            </FormField>

            <FormField
              label="Agent Prompt"
              description="The prompt that defines the agent's behavior and instructions"
            >
              <Textarea
                value={prompt}
                onChange={({ detail }) => setPrompt(detail.value)}
                disabled={isLoading}
                placeholder="Enter the agent's prompt and instructions..."
                rows={4}
              />
            </FormField>

            <FormField
              label="Agent Type"
              description="Select the type of agent to create"
            >
              <Select
                selectedOption={(() => {
                  return (
                    agentTypeOptions.find(
                      (option) => option.value === agentType
                    ) || agentTypeOptions[0]
                  );
                })()}
                onChange={({ detail }) => {
                  console.log("Full detail object:", detail);
                  console.log("selectedOption:", detail.selectedOption);
                  console.log(
                    "selectedOption.value:",
                    detail.selectedOption?.value
                  );
                  console.log(
                    "AgentTypes.AmazonAthena:",
                    AgentTypes.AmazonAthena
                  );

                  if (detail.selectedOption?.value) {
                    setAgentType(detail.selectedOption.value);
                  }
                }}
                options={agentTypeOptions}
                disabled={isLoading || isEditing} // Disable type change when editing
              />
            </FormField>

            {agentType === AgentTypes.KnowledgeBase && (
              <FormField
                label="Knowledge Base ID"
                description="The ID of the knowledge base this agent will use. Ensure that the appropriate IAM permissions are set for this agent to access the knowledge base."
              >
                <Input
                  value={knowledgeBaseId}
                  onChange={({ detail }) => setKnowledgeBaseId(detail.value)}
                  disabled={isLoading}
                  placeholder="Enter knowledge base ID"
                />
              </FormField>
            )}

            {agentType === AgentTypes.RestApi && (
              <FormField
                label="API Endpoint"
                description="The REST API endpoint this agent will call"
              >
                <Input
                  value={apiEndpoint}
                  onChange={({ detail }) => setApiEndpoint(detail.value)}
                  disabled={isLoading}
                  placeholder="https://api.example.com/endpoint"
                />
              </FormField>
            )}

            {agentType === AgentTypes.AmazonAthena && (
              <>
                <FormField
                  label="Athena Database"
                  description="The name of the Athena database this agent will query. Ensure that the appropriate IAM permissions are set for this agent to access Athena."
                >
                  <Input
                    value={athenaDatabase}
                    onChange={({ detail }) => setAthenaDatabase(detail.value)}
                    disabled={isLoading}
                    placeholder="Enter Athena database name"
                  />
                </FormField>

                <FormField
                  label="Athena Query"
                  description="The SQL query this agent will execute in Athena"
                >
                  <Textarea
                    value={athenaQuery}
                    onChange={({ detail }) => setAthenaQuery(detail.value)}
                    disabled={isLoading}
                    placeholder="SELECT * FROM table_name WHERE condition..."
                    rows={4}
                  />
                </FormField>
              </>
            )}
          </SpaceBetween>
        </Form>
      </SpaceBetween>
    </Container>
  );
};

export default AgentDetails;
