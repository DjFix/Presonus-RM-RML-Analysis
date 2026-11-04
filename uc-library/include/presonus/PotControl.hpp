#pragma once

#include "core/portable/gui/corecontrols.h"

// Partial source port. Provider relationships are evidence-backed;
// these declarations do not establish firmware layouts or ARM ABI.
namespace Presonus {
class PotControl : public Core::Portable::Control {
public:
  explicit PotControl(const Core::TRect<int> &size);
  ~PotControl() override;
  void setAttributes(const Core::Portable::Attributes &a) override;
  void draw(const Core::Portable::DrawEvent &e) override;
  virtual void changeFrames();
  virtual void setFrame(int frame);

  // Independent portable observation API, not recovered original interfaces.
  struct PortableState {
    Core::Portable::Bitmap *image;
    Core::Portable::Bitmap *strip;
    Core::Portable::Bitmap *slice;
    int focusMode;
    int previousValue;
    int frameCount;
    int options;
  };
  void portableBindBitmaps(Core::Portable::Bitmap *image,
                           Core::Portable::Bitmap *strip,
                           Core::Portable::Bitmap *slice) {
    image_.assign(image);
    focusStrip_.assign(strip);
    focusSlice_.assign(slice);
  }
  void portableBindDrawState(int mode, int frame, int count, int flags) {
    focusMode_ = mode;
    previousValue_ = frame;
    frameCount_ = count;
    options = flags;
  }
  PortableState portableState() const;

protected:
  Core::Portable::BitmapReference image_, focusStrip_, focusSlice_;
  int focusMode_;
  int previousValue_;
  int frameCount_;
};
} // namespace Presonus
