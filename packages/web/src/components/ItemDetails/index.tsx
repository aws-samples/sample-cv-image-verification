import {
  Box,
  Button,
  Form,
  FormField,
  Input,
  SpaceBetween,
  Tabs,
  Textarea,
  TextContent,
  Alert,
  Link,
  Multiselect,
} from "@cloudscape-design/components";
import { FilteringRulesDetail } from "../FilteringRulesDetail";
import { useEffect, useState } from "react";

import { useCreateItem, useGetItem, useUpdateItem } from "../../hooks/Items";
import { useGetAllAgents } from "../../hooks/Agents";
import {
  DescriptionFilteringRule,
  LabelFilteringRule,
  Agent,
} from "@aws-samples/cv-verification-api-client/src";
import { useAppLayoutContext } from "../../App";

export interface ItemDetailsProps {
  itemId?: string;
}

interface AgentOption {
  label: string;
  value: string;
  description: string | undefined;
}

export const ItemDetails: React.FC<ItemDetailsProps> = (
  props: ItemDetailsProps
) => {
  const { data: loadedItem } = useGetItem(props?.itemId);
  const { data: allAgents } = useGetAllAgents();
  const updateItemMutation = useUpdateItem(props?.itemId);
  const createItemMutation = useCreateItem();
  const [name, setName] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [labelFilteringRules, setLabelFilteringRules] = useState<
    LabelFilteringRule[]
  >([]);
  const [descriptionFilteringRules, setDescriptionFilteringRules] = useState<
    DescriptionFilteringRule[]
  >([]);
  const [selectedAgentIds, setSelectedAgentIds] = useState<AgentOption[]>([]);

  const [isSaving, setIsSaving] = useState<boolean>(false);
  // Add Alert State
  const [alertVisible, setAlertVisible] = useState(false);
  const [alertType, setAlertType] = useState<"success" | "error">("success");
  const [alertMessage, setAlertMessage] = useState("");
  const [clusterNumber, setClusterNumber] = useState("");

  const appLayout = useAppLayoutContext();

  useEffect(() => {
    appLayout.setAppLayoutProps({
      breadcrumbs: (
        <>
          <Box display="inline">
            / <Link href="/items">Items</Link> / Edit Item{" "}
            {loadedItem ? loadedItem.name : props.itemId}
          </Box>
        </>
      ),
    });
  }, [loadedItem, props.itemId]);

  // --- Alert Handling Callbacks ---
  const handleSaveSuccess = (message = "Item saved successfully.") => {
    setAlertMessage(message);
    setAlertType("success");
    setAlertVisible(true);
    // Auto-dismiss success alert after 5 seconds
    setTimeout(() => setAlertVisible(false), 5000);
  };

  const handleSaveError = (error: unknown, action = "save") => {
    const errorDetail =
      error instanceof Error ? error.message : "An unknown error occurred.";
    setAlertMessage(`Failed to ${action} item: ${errorDetail}`);
    setAlertType("error");
    setAlertVisible(true);
    // Error alerts require manual dismissal
  };

  useEffect(() => {
    if (loadedItem) {
      setName(loadedItem.name);
      setClusterNumber(loadedItem.clusterNumber?.toString() ?? "");
      setDescription(loadedItem.description);
      setLabelFilteringRules(loadedItem.labelFilteringRules ?? []);
      setDescriptionFilteringRules(loadedItem.descriptionFilteringRules ?? []);

      // Set selected agents from loaded item
      if (loadedItem.agentIds && allAgents) {
        const selectedOptions: AgentOption[] = loadedItem.agentIds
          .map((agentId) => {
            const agent = allAgents.find((a: Agent) => a.id === agentId);
            return agent
              ? {
                  label: `${agent.name} (${agent.type})`,
                  value: agent.id,
                  description: agent.description || undefined,
                }
              : null;
          })
          .filter((option): option is AgentOption => option !== null);
        setSelectedAgentIds(selectedOptions);
      }
    }
  }, [loadedItem, allAgents]);

  // Create agent options for multiselect
  const agentOptions: AgentOption[] =
    allAgents?.map((agent: Agent) => ({
      label: `${agent.name} (${agent.type})`,
      value: agent.id,
      description: agent.description || undefined,
    })) ?? [];

  // Update handler signature and implementation to use local type
  const handleFilteringRulesChange = (rules: {
    labelRules: LabelFilteringRule[];
    descriptionRules: DescriptionFilteringRule[];
  }) => {
    setLabelFilteringRules(rules.labelRules);
    setDescriptionFilteringRules(rules.descriptionRules);
  };

  const handleSave = () => {
    setIsSaving(true);
    if (clusterNumber) {
      // Validate that clusterNumber is an integer
      if (
        !/^\d+$/.test(clusterNumber) ||
        !Number.isInteger(Number(clusterNumber))
      ) {
        handleSaveError(
          new Error("Cluster Number must be an integer"),
          "validate"
        );
        setIsSaving(false);
        return;
      }
    }

    const agentIds = selectedAgentIds.map((option) => option.value);
    console.log("Selected Agent IDs:", agentIds);
    if (props.itemId) {
      updateItemMutation.mutate(
        {
          name,
          description,
          labelFilteringRules,
          clusterNumber: clusterNumber ? Number(clusterNumber) : undefined,
          descriptionFilteringRules,
          agentIds,
        },
        {
          onSuccess: () => {
            setIsSaving(false);
            handleSaveSuccess(); // Call alert handler
          },
          onError: (error) => {
            console.error("Failed to save item:", error);
            setIsSaving(false);
            handleSaveError(error, "save"); // Call alert handler
          },
        }
      );
    } else {
      createItemMutation.mutate(
        {
          name,
          description,
          clusterNumber: clusterNumber ? Number(clusterNumber) : undefined,
          labelFilteringRules,
          descriptionFilteringRules,
          agentIds,
        },
        {
          onSuccess: (data) => {
            setIsSaving(false);
            handleSaveSuccess("Item created successfully."); // Call alert handler
            if (data?.id) {
              window.location.href = `/itemdetail/${data.id}`;
            }
          },
          onError: (error) => {
            console.error("Failed to create item:", error);
            setIsSaving(false);
            handleSaveError(error, "create"); // Call alert handler
          },
        }
      );
    }
  };

  return (
    <SpaceBetween size="m">
      {/* Render Alert */}
      {alertVisible && (
        <Alert
          type={alertType}
          dismissible
          onDismiss={() => setAlertVisible(false)}
          header={alertType === "success" ? "Success" : "Error"}
        >
          {alertMessage}
        </Alert>
      )}
      <Box>
        <h3>{props.itemId ? "Edit" : "Create"} Item</h3>
      </Box>
      <Box textAlign="right">
        <Button variant="primary" onClick={handleSave} loading={isSaving}>
          Save
        </Button>
      </Box>

      <Tabs
        tabs={[
          {
            id: "general",
            label: "General Information",
            content: (
              <Form>
                <FormField label="Name">
                  <Input
                    onChange={(e) => {
                      setName(e.detail.value);
                    }}
                    value={name}
                  />
                </FormField>
                <FormField label="Description">
                  <Textarea
                    rows={10}
                    onChange={(e) => setDescription(e.detail.value)}
                    value={description}
                  />
                </FormField>
                <FormField
                  description="Optional cluster identifier this rule belongs to. For a cluster to be marked as compliant, all rules in it must be satisfied."
                  label="Cluster Number"
                >
                  <Input
                    value={clusterNumber}
                    onChange={(e) => setClusterNumber(e.detail.value)}
                  ></Input>
                </FormField>
                <FormField
                  description="Select agents to associate with this item. Agents can assist with item description modification and processing."
                  label="Agents"
                >
                  <Multiselect
                    selectedOptions={selectedAgentIds}
                    onChange={({ detail }) =>
                      setSelectedAgentIds(
                        detail.selectedOptions as AgentOption[]
                      )
                    }
                    options={agentOptions}
                    placeholder="Select agents..."
                    filteringType="auto"
                    tokenLimit={3}
                    i18nStrings={{
                      tokenLimitShowMore: "Show more",
                      tokenLimitShowFewer: "Show fewer",
                    }}
                  />
                </FormField>
              </Form>
            ),
          },
          {
            id: "filtering-rules",
            label: "Filtering Rules",
            content: props.itemId ? (
              <FilteringRulesDetail
                selectedAgentIds={selectedAgentIds?.map((a) => a.value) ?? []}
                itemId={props.itemId}
                labelRules={labelFilteringRules}
                descriptionRules={descriptionFilteringRules}
                onRulesChange={handleFilteringRulesChange}
                onSaveSuccess={() =>
                  handleSaveSuccess("Filtering rules saved successfully.")
                } // Pass down alert handlers
                onSaveError={(error) =>
                  handleSaveError(error, "save filtering rules")
                } // Pass down alert handlers
              />
            ) : (
              <Box textAlign="center" padding="l">
                <TextContent>
                  <h3>Save the item first to manage filtering rules</h3>
                  <p>
                    You need to save this item before you can add filtering
                    rules.
                  </p>
                </TextContent>
              </Box>
            ),
          },
        ]}
      />
    </SpaceBetween>
  );
};
