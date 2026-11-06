#pragma once
#include "core/portable/gui/corebitmap.h"
#include "core/public/coreformatter.h"
#include "core/public/corevector.h"
#include "presonus/BackgroundPainter.hpp"
#include "presonus/IBackgroundGridProvider.hpp"
#include <memory>
namespace presonus::grid_port {
// Independent source-port state, never original ARM object fields.
struct AxisState {
  int orientation = 0;
  const Core::Formatter *formatter = nullptr;
};
} // namespace presonus::grid_port
namespace Presonus {
// Portable composition with original encoded interfaces. Original inheritance,
// layout, ordinary return declarations and ARM ABI remain unresolved.
class GridPainter : public BackgroundPainter {
public:
  enum Axis : int {};
  enum LabelOrientation : int {};
  GridPainter(presonus::grid_port::AxisState &first,
              presonus::grid_port::AxisState &second)
      : first_(first), second_(second) {}
  explicit GridPainter(IBackgroundGridProvider &provider);
  ~GridPainter() override;
  GridPainter(const GridPainter &) = delete;
  GridPainter &operator=(const GridPainter &) = delete;
  void setGridOrientation(Axis, LabelOrientation, const char *);
  // Negative/zero counts clear; positive counts require readable nonaliasing
  // source storage. Native allocation failure is outside the supported domain.
  // Native method does NOT invalidate an existing bitmap.
  void setGridValues(Axis, const float *, int);
  void paint(const Core::TRect<int> &, const Core::Portable::DrawEvent &,
             const Core::Portable::Style &) override;
  void paintGrid(const Core::TRect<int> &, const Core::TRect<int> &,
                 const Core::Portable::DrawEvent &,
                 const Core::Portable::Style &);
  // Explicit source-port setup; these are not recovered original methods.
  void setPortableDrawingOptions(bool cached, bool labels) {
    cached_ = cached;
    labels_ = labels;
  }
  const Core::Vector<float> &portableValues(Axis axis) const {
    return static_cast<int>(axis) == 0 ? xValues_ : yValues_;
  }
  const Core::Portable::Bitmap *portableBitmap() const { return bitmap_.get(); }
  const Core::Rect &portableRectangle() const { return rectangle_; }

private:
  presonus::grid_port::AxisState ownedFirst_, ownedSecond_;
  presonus::grid_port::AxisState &first_;
  presonus::grid_port::AxisState &second_;
  IBackgroundGridProvider *provider_ =
      nullptr; // borrowed; must outlive painter
  // Parentheses select capacity/growth, avoiding Vector initializer-list
  // values.
  Core::Vector<float> xValues_ = Core::Vector<float>(0, 5);
  Core::Vector<float> yValues_ = Core::Vector<float>(0, 5);
  bool cached_ = false, labels_ = false;
  Core::Rect rectangle_;
  // Last member releases before either vector, as in native destructor.
  std::unique_ptr<Core::Portable::Bitmap> bitmap_;
};
} // namespace Presonus
