/**********************************************************************************************************************
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                *
 *                                                                                                                    *
 *  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *     https://aws.amazon.com/asl/                                                                                    *
 *                                                                                                                    *
 *  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 **********************************************************************************************************************/

/*! Copyright [Amazon.com](http://amazon.com/), Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0 */
import { useCognitoAuthContext } from "@aws-northstar/ui";
import NavHeader from "@aws-northstar/ui/components/AppLayout/components/NavHeader";
import getBreadcrumbs from "@aws-northstar/ui/components/AppLayout/utils/getBreadcrumbs";
import {
  BreadcrumbGroup,
  BreadcrumbGroupProps,
  SideNavigation,
  SideNavigationProps,
} from "@cloudscape-design/components";
import AppLayout, {
  AppLayoutProps,
} from "@cloudscape-design/components/app-layout";
import * as React from "react";
import { createContext, useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Config from "./config.json";
import Routes from "./Routes";

// Deep equality check for objects
const deepEqual = (obj1: unknown, obj2: unknown): boolean => {
  if (obj1 === obj2) return true;

  if (obj1 == null || obj2 == null) return obj1 === obj2;

  if (typeof obj1 !== typeof obj2) return false;

  if (typeof obj1 !== "object") return obj1 === obj2;

  const keys1 = Object.keys(obj1 as Record<string, unknown>);
  const keys2 = Object.keys(obj2 as Record<string, unknown>);

  if (keys1.length !== keys2.length) return false;

  for (const key of keys1) {
    if (!keys2.includes(key)) return false;
    if (
      !deepEqual(
        (obj1 as Record<string, unknown>)[key],
        (obj2 as Record<string, unknown>)[key]
      )
    )
      return false;
  }

  return true;
};

/**
 * Context for updating/retrieving the AppLayout.
 */
export const AppLayoutContext = createContext({
  appLayoutProps: {},
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  setAppLayoutProps: (_: AppLayoutProps) => {},
});

/**
 * Custom hook for accessing the AppLayoutContext.
 */
export const useAppLayoutContext = () => {
  const appLayoutContext = React.useContext(AppLayoutContext);
  if (!appLayoutContext) {
    throw new Error(
      "useAppLayoutContext must be used within an AppLayoutContextProvider"
    );
  }
  return appLayoutContext;
};

export const NavItems: SideNavigationProps.Item[] = [
  { text: "Home", type: "link", href: "/" },
  { type: "divider" },
  { text: "Agents", type: "link", href: "/agents" },
  { text: "Items", type: "link", href: "/items" },
  { text: "Collections", type: "link", href: "/collections" },
  { text: "Verification Jobs", type: "link", href: "/verificationjobs" },

  { type: "divider" },
  {
    text: "Configuration",
    type: "link",
    href: "/config",
  },
];

/**
 * Defines the App layout and contains logic for routing.
 */
const App: React.FC = () => {
  const [username, setUsername] = useState<string | undefined>();
  const [email, setEmail] = useState<string | undefined>();
  const { getAuthenticatedUser } = useCognitoAuthContext();

  const navigate = useNavigate();
  const [activeHref, setActiveHref] = useState("/");
  const [activeBreadcrumbs, setActiveBreadcrumbs] = useState<
    BreadcrumbGroupProps.Item[]
  >([{ text: "/", href: "/" }]);
  const [appLayoutProps, setAppLayoutProps] = useState<AppLayoutProps>({});
  const location = useLocation();

  useEffect(() => {
    if (getAuthenticatedUser) {
      const authUser = getAuthenticatedUser();
      setUsername(authUser?.getUsername());

      authUser?.getSession(() => {
        authUser.getUserAttributes((_, attributes) => {
          setEmail(attributes?.find((a) => a.Name === "email")?.Value);
        });
      });
    }
  }, [getAuthenticatedUser, setUsername, setEmail]);

  const setAppLayoutPropsSafe = useCallback(
    (props: AppLayoutProps) => {
      if (!deepEqual(appLayoutProps, props)) {
        setAppLayoutProps(props);
      }
    },
    [appLayoutProps]
  );

  useEffect(() => {
    setActiveHref(location.pathname);
    const navItem = NavItems.find(
      (item) => item.type === "link" && item.href === location.pathname
    );
    const title = navItem
      ? (navItem as SideNavigationProps.Link).text
      : location.pathname;
    const breadcrumbs = getBreadcrumbs(title, location.search, "/");
    setActiveBreadcrumbs(breadcrumbs);
  }, [location]);

  const onNavigate = useCallback(
    (e: CustomEvent<{ href: string; external?: boolean }>) => {
      if (!e.detail.external) {
        e.preventDefault();
        setAppLayoutPropsSafe({
          contentType: undefined,
          splitPanelOpen: false,
          splitPanelSize: undefined,
          splitPanelPreferences: undefined,
        });
        navigate(e.detail.href);
      }
    },
    [navigate]
  );

  return (
    <AppLayoutContext.Provider
      value={{ appLayoutProps, setAppLayoutProps: setAppLayoutPropsSafe }}
    >
      <NavHeader
        title={Config.applicationName}
        logo={Config.logo}
        user={
          username
            ? {
                username: email ?? "",
                email,
              }
            : undefined
        }
        onSignout={() =>
          new Promise(() => {
            const user = getAuthenticatedUser();
            if (user) {
              user.signOut();
            }
            window.location.href = "/";
          })
        }
      />
      <AppLayout
        breadcrumbs={
          <BreadcrumbGroup onFollow={onNavigate} items={activeBreadcrumbs} />
        }
        toolsHide
        navigation={
          <SideNavigation
            header={{ text: Config.applicationName, href: "/" }}
            activeHref={activeHref}
            onFollow={onNavigate}
            items={NavItems}
          />
        }
        content={<Routes />}
        {...appLayoutProps}
      />
    </AppLayoutContext.Provider>
  );
};

export default App;
