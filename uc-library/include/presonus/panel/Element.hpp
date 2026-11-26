#pragma once
#include "presonus/panel/ElementInfo.hpp"
#include "presonus/surface_panel/IDisplay.hpp"

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
  explicit Element(const ElementInfo &info);
  const ElementInfo &sourceInfo() const { return info_; }
  Rectangle &drawingBounds() { return bounds_; }
  const Rectangle &drawingBounds() const { return bounds_; }
  virtual ~Element();

  virtual void activate(int mode);
  virtual bool needsToDraw() const;
  virtual void setNeedsToDraw(bool dirty);

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
  virtual void render(IDisplay &display, bool force);
  virtual void draw(IDisplay &display);
  virtual bool editable();

  virtual unsigned int deltaEncoder(int delta);
  virtual unsigned int tap();
  virtual unsigned int next();
  unsigned int getParam();
  virtual unsigned int previous();

private:
  ElementInfo info_;
  Rectangle bounds_{0, 0, 0, 0};
  State elementState_;
};
} // namespace Presonus::Panel
