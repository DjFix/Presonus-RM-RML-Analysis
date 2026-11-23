#pragma once

namespace Presonus::Panel {
class IDisplay;

// Partial portable source model of the observed no-op base operations.
// The original ordinary return declarations are unresolved: an ARM zero result
// cannot distinguish bool, integer or pointer. unsigned int is a portable
// observation carrier. The virtual destructor models the observed base
// teardown. Original fields, inheritance and vtable layout remain unresolved.
class Element {
public:
  Element() = default;
  Element(int x, int y);
  virtual ~Element();

  virtual void activate(int mode);
  virtual bool needsToDraw() const;

  struct State {
    int x = 0;
    int y = 0;
    unsigned int dirty = 1;
    int activation = 0;
  };
  const State &elementState() const { return elementState_; }
  void setDirty(unsigned int value) { elementState_.dirty = value; }

  // Portable base call. The firmware had a virtual slot for render, but the
  // original table and unencoded return declaration are still unresolved.
  void render(IDisplay &display, bool force);

  unsigned int deltaEncoder(int delta);
  unsigned int tap();
  unsigned int next();
  unsigned int getParam();
  unsigned int previous();

private:
  State elementState_;
};
} // namespace Presonus::Panel
