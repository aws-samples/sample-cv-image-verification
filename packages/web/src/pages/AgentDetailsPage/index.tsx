import { Box, Link } from "@cloudscape-design/components";
import { useAppLayoutContext } from "../../App";
import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGetAgent } from "../../hooks/Agents";
import AgentDetails from "../../components/AgentDetails";

export const AgentDetailsPage: React.FC = () => {
  const appLayout = useAppLayoutContext();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { data: agent } = useGetAgent(id);

  useEffect(() => {
    appLayout.setAppLayoutProps({
      breadcrumbs: (
        <>
          <Box display="inline">
            {" "}
            / <Link href="/agents">Agents</Link> / Edit Agent{" "}
            {agent ? agent.name : id}
          </Box>
        </>
      ),
    });
  }, []);

  const handleSave = () => {
    navigate(`/agents`);
  };

  const handleCancel = () => {
    navigate("/agents");
  };

  return (
    <Box padding="m">
      <AgentDetails agent={agent} onSave={handleSave} onCancel={handleCancel} />
    </Box>
  );
};
