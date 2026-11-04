#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus {
class IMappingController;
}
#include <cstdint>
namespace presonus::surface {
// Independent application boundary. Does not claim the original object layout.
struct DawFxBindings {
  void *context;
  bool (*hasFolder)(void *);
  std::int32_t (*usedCount)(void *);
  void (*updateList)(void *, bool);
};
} // namespace presonus::surface
namespace Presonus::Surface {
// Portable source port; original return declarations and ARM layout unresolved.
class DawFxPageComponent : public Core::Portable::Component {
public:
  ~DawFxPageComponent();
  void setMappingController(Presonus::IMappingController *);
  DawFxPageComponent(Core::Portable::Parameter *mode,
                     presonus::surface::DawFxBindings bindings,
                     int insertOffset = 0, int sendOffset = 0);
  void setListOffset(int offset);
  void addListOffset(int delta);
  int getMaxListOffset() const;
  int &getListOffset() const;
  bool isSendMode() const;

private:
  friend struct DawFxTestAccess;
  Presonus::IMappingController *mappingController_{};
  Core::Portable::Parameter *mode_;
  presonus::surface::DawFxBindings bindings_;
  mutable int insertOffset_, sendOffset_;
};
} // namespace Presonus::Surface
