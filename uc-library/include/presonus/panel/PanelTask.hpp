#pragma once
#include <cstdint>
namespace Presonus::Panel {
// Portable virtual interface: original return spelling and object layout remain
// unresolved. Native PanelTask::idle returns zero. Scheduling borrows pointers.
class PanelTask {
public:
  virtual bool idle();
  virtual ~PanelTask() = default;
};
} // namespace Presonus::Panel
