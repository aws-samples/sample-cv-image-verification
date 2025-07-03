import {
  Authenticator,
  Theme,
  ThemeProvider,
  useTheme,
} from "@aws-amplify/ui-react";
import React, {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Amplify } from "aws-amplify";
import { getCurrentUser } from "aws-amplify/auth";
import { Hub } from "aws-amplify/utils";

/**
 * Context for storing the runtimeContext.
 */
export const RuntimeConfigContext = createContext<any>({});

/**
 * Sets up the runtimeContext and Cognito auth.
 *
 * This assumes a runtime-config.json file is present at '/'. In order for Auth to be set up automatically,
 * the runtime-config.json must have the following properties configured: [region, userPoolId, userPoolWebClientId, identityPoolId].
 */
const Auth: React.FC<any> = ({ children }) => {
  const [runtimeContext, setRuntimeContext] = useState<any>(undefined);
  const { tokens } = useTheme();

  // Customize your login theme
  const theme: Theme = useMemo(
    () => ({
      name: "AuthTheme",
      tokens: {
        components: {
          passwordfield: {
            button: {
              _hover: {
                backgroundColor: {
                  value: "white",
                },
                borderColor: {
                  value: tokens.colors.blue["40"].value,
                },
              },
            },
          },
        },
        colors: {
          background: {
            primary: {
              value: tokens.colors.neutral["20"].value,
            },
            secondary: {
              value: tokens.colors.neutral["100"].value,
            },
          },
          brand: {
            primary: {
              10: tokens.colors.blue["20"],
              80: tokens.colors.blue["40"],
              90: tokens.colors.blue["40"],
              100: tokens.colors.blue["40"],
            },
          },
        },
      },
    }),
    [tokens]
  );

  useEffect(() => {
    fetch("/runtime-config.json")
      .then((response) => {
        return response.json();
      })
      .then((runtimeCtx) => {
        if (
          runtimeCtx.userPoolId &&
          runtimeCtx.userPoolWebClientId &&
          runtimeCtx.identityPoolId
        ) {
          Amplify.configure({
            Auth: {
              Cognito: {
                signUpVerificationMethod: "code",
                userPoolId: runtimeCtx.userPoolId,
                userPoolClientId: runtimeCtx.userPoolWebClientId,
                //identityPoolId: runtimeCtx.identityPoolId,
                loginWith: {
                  // OPTIONAL - Hosted UI configuration
                  oauth: {
                    domain: runtimeCtx.authDomain,
                    scopes: [
                      "phone",
                      "email",
                      "profile",
                      "openid",
                      "aws.cognito.signin.user.admin",
                    ],
                    redirectSignIn: runtimeCtx.redirectSignIn,
                    redirectSignOut: runtimeCtx.redirectSignOut,
                    responseType: "code", // or 'token', note that REFRESH token will only be generated when the responseType is code
                  },
                },
              },
            },
          });
          setRuntimeContext(runtimeCtx);
          getCurrentUser()
            .then((user) => {
              setRuntimeContext({ ...runtimeCtx, user });
            })
            .catch((e) => console.error(`currentUserInfo() error - ${e}`));
        } else {
          console.warn(
            "runtime-config.json should have region, userPoolId, userPoolWebClientId & identityPoolId."
          );
        }
      })
      .catch(() => {
        console.warn(
          "unable to load runtime-config.json from public directory"
        );
        setRuntimeContext({});
      });
  }, [setRuntimeContext]);

  const setRuntimeContextForUser = () => {
    getCurrentUser()
      .then((user: any) => {
        setRuntimeContext((prevRuntimeContext: any) => ({
          ...prevRuntimeContext,
          user,
        }));
      })
      .catch((e: any) => console.error(e));
  };

  useEffect(() => {
    Hub.listen("auth", (data: any) => {
      switch (data.payload.event) {
        case "signedIn":
          console.log("Sign in successful");
          setRuntimeContextForUser();
          break;
        case "signedOut":
          console.log("Sign out successful");
          break;

        case "signInWithRedirect":
          console.log("Sign in successful");
          setRuntimeContextForUser();
          break;
        case "signInWithRedirect_failure":
          console.log("Sign in failed");
          break;
      }
    });
  }, []);

  const AuthWrapper: React.FC<any> = useCallback(
    ({ children: _children }) => (
      <ThemeProvider theme={theme}>
        <Authenticator
          initialState={"signIn"}
          variation="modal"
          loginMechanisms={["email"]}
        >
          {_children}
        </Authenticator>
      </ThemeProvider>
    ),
    [runtimeContext, theme]
  );

  return (
    <AuthWrapper>
      <RuntimeConfigContext.Provider
        value={{ runtimeContext, setRuntimeContext }}
      >
        {children}
      </RuntimeConfigContext.Provider>
    </AuthWrapper>
  );
};

export default Auth;
