#pragma once

#include "core/portable/coreparams.h"
#include "core/public/corevector.h"
#include <cstdint>

namespace Core::Portable {
class Component;
}

namespace presonus::surface {
// Explicit source-port state. These fields do not describe the ARM object
// layout.
struct GroupsPageState {
  std::int32_t listOffset = 0;
  std::int32_t selection = -1;
  Core::ConstVector<Core::Portable::Parameter *> selectionParameters{nullptr,
                                                                     0};
  Core::ConstVector<Core::Portable::Component *> firstGroups{nullptr, 0};
  Core::ConstVector<Core::Portable::Component *> secondGroups{nullptr, 0};
  Core::Portable::Component *observedGroup = nullptr;
};
// App-specific boundaries remain unresolved; caller must provide them. There
// are no default/no-op production providers. Tests capture calls at this seam.
struct GroupsPageDependencies {
  virtual ~GroupsPageDependencies() = default;
  virtual void refreshList() = 0;
  virtual void doselect() = 0;
  virtual void observeGroup(Core::Portable::Component *) = 0;
};
} // namespace presonus::surface

namespace Presonus::Surface {
// Portable contract, original inheritance/layout and unencoded returns pending.
class GroupsPageComponent {
public:
  GroupsPageComponent(presonus::surface::GroupsPageState &state,
                      presonus::surface::GroupsPageDependencies &dependencies)
      : state(state), dependencies(dependencies) {}
  void addListOffset(int delta);
  int getMaxListOffset() const;
  void setListOffset(int offset);
  void deSelect();
  void updateSelection();

private:
  presonus::surface::GroupsPageState &state;
  presonus::surface::GroupsPageDependencies &dependencies;
};
} // namespace Presonus::Surface
