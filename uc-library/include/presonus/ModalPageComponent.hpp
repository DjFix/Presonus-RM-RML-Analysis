#pragma once
namespace Presonus {
// Bounded portable source model. Original inheritance/layout and ordinary
// return spelling remain unresolved. This object owns no resources and castTo
// borrows this object's lifetime; it performs no Core or other provider
// execution.
class ModalPageComponent {
public:
  void *castTo(int classId);

  // Portable bool models the native result tested by the modal caller.
  bool onOk();
  bool onCancel();
};
} // namespace Presonus
