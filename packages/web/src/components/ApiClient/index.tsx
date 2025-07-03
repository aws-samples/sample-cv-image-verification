import { useContext, useMemo } from "react";
import { RuntimeConfigContext } from "../RuntimeContext";
import useSigV4Client from "@aws-northstar/ui/components/CognitoAuth/hooks/useSigv4Client";
import { Configuration } from "@aws-samples/cv-verification-api-client/src/runtime";
import { CVImageVerificationApi } from "@aws-samples/cv-verification-api-client/src";

export const useApiClient = () => {
  const client = useSigV4Client();
  const runtimeContext = useContext(RuntimeConfigContext);

  return useMemo(() => {
    return runtimeContext?.apiUrl
      ? new CVImageVerificationApi(
          new Configuration({
            basePath: runtimeContext.apiUrl,
            fetchApi: client,
          })
        )
      : undefined;
  }, [client, runtimeContext?.apiUrl]);
};
