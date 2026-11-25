#pragma once

#include "core/portable/gui/coreviewcontroller.h"

namespace Presonus {
class MappingTable;

namespace Surface {
class ScribbleStripController : public Core::Portable::ViewController {
public:
  // Portable construction with borrowed providers that outlive the controller.
  // The native SurfaceApplication initializes the corresponding state inline.
  ScribbleStripController(int index, MappingTable &mapping,
                          Core::Portable::ViewController &root)
      : index_(index), mapping_(mapping), root_(root) {}
  ~ScribbleStripController() override;

  void *castTo(TypeID type) override;
  Core::Portable::View *createView(const char *type) override;
  void *getObjectForView(const char *name, const char *type) override;

private:
  int index_;
  MappingTable &mapping_;
  Core::Portable::ViewController &root_;
};
} // namespace Surface
} // namespace Presonus
