// Copyright (C) 2021 Monocle authors
// SPDX-License-Identifier: AGPL-3.0-or-later
//
// The main component
//
open Prelude

module MonocleNav = {
  @react.component
  let make = (~active: string, ~store: Store.t) => {
    let (state, _) = store

    let navItem = (name, dest) => {
      let navUrl =
        "/" ++
        state.index ++
        dest ++
        switch state.query {
        | "" => ""
        | q => "?q=" ++ q
        }

      <NavItem
        key={name}
        onClick={_ => navUrl->RescriptReactRouter.push}
        isActive={active == dest}
        preventDefault={true}
        _to={navUrl}>
        {name->str}
      </NavItem>
    }

    let navGroup = (title, xs) =>
      <NavGroup title key={title}>
        {xs->Belt.List.map(((a, b)) => navItem(a, b))->Belt.List.toArray->React.array}
      </NavGroup>

    <Nav>
      <NavList>
        {[
          navItem("Activity", "/"),
          navGroup(
            "People",
            list{
              ("Active authors", "/active_authors"),
              ("Peers strength", "/peers_strength"),
              ("New contributors", "/new_authors"),
              ("Groups", "/user_groups"),
            },
          ),
          navGroup("Projects", list{("Repositories", "/repos")}),
          navGroup("Changes", list{("Browse Changes", "/changes"), ("Board", "/board")}),
        ]->React.array}
      </NavList>
    </Nav>
  }
}

module Footer = {
  @react.component
  let make = () =>
    <Nav variant=#Horizontal>
      <NavList>
        <a
          className="nav-link"
          href="https://changemetrics.io"
          target="_blank"
          rel="noopener noreferrer">
          {"Powered by Monocle"->str}
        </a>
      </NavList>
    </Nav>
}

@react.component
let make = () => {
  let url = RescriptReactRouter.useUrl()

  // The initial index
  let initIndex = switch url.path->Belt.List.head->Belt.Option.getWithDefault("") {
  | "help" => ""
  | x => x
  }

  // The current nav
  let active = switch url.path {
  | list{} => ""
  | list{_, ...xs} => "/" ++ Js.Array.joinWith("/", xs->Belt.List.toArray)
  }

  let store = Store.use(initIndex)
  let (state, _) = store

  let _topNav = <Nav variant=#Horizontal> {<> </>} </Nav>
  let topSearch = <PageHeaderTools> <Search.Top store /> </PageHeaderTools>
  let headerTools = state.index == "" ? React.null : topSearch
  let nav = <MonocleNav active store />
  let sidebar = state.index == "" ? React.null : <PageSidebar nav />
  let logo = <span onClick={_ => store->Store.changeIndex("")}> {"Monocle"->str} </span>
  let header = <PageHeader logo headerTools />
  // This sep prevent footer from hidding page content, not pretty but this works!
  let sep = {<> <br /> <br /> <br /> </>}

  <Page header sidebar isManagedSidebar={true}>
    <PageSection isFilled={true}>
      {switch url.path {
      | list{} => <Indices.Indices store />
      | list{"help", "search"} => <HelpSearch.View store />
      | list{_} => <Activity store />
      | list{_, "active_authors"} => <ActivePeopleView store />
      | list{_, "peers_strength"} => <PeersStrengthView store />
      | list{_, "new_authors"} => <NewContributorsView store />
      | list{_, "user_groups"} => <GroupsView store />
      | list{_, "user_groups", group} => <GroupView group store />
      | list{_, "repos"} => <ReposView store />
      | list{_, "changes"} => <NChangeView store />
      | list{_, "change", change} => <ChangeView change store />
      | list{_, "board"} => <Board store />
      | _ => <p> {"Not found"->str} </p>
      }}
      {sep}
    </PageSection>
    <PageSection variant=#Light sticky=#Bottom className="footer"> <Footer /> </PageSection>
  </Page>
}

let default = make