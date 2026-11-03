#pragma once

#include "core/portable/gui/corecontrols.h"

// Partial source ports. Native base-constructor calls establish these provider
// relationships. These declarations do not establish firmware layouts or ABI.
namespace Presonus {
class PotControl : public Core::Portable::Control {
public:
  explicit PotControl(const Core::TRect<int> &size);
  void setAttributes(const Core::Portable::Attributes &a) override;

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
  PortableState portableState() const;

protected:
  Core::Portable::BitmapReference image_, focusStrip_, focusSlice_;
  int focusMode_;
  int previousValue_;
  int frameCount_;
};

class FocusHelperButton : public Core::Portable::RadioButton {
public:
  FocusHelperButton(const Core::TRect<int> &size,
                    Core::Portable::Parameter *parameter, int value);
  void setAttributes(const Core::Portable::Attributes &a) override;

  // Independent portable observations. viewName_ borrows Attributes storage;
  // the hosting application must preserve that storage while using the pointer.
  const char *portableViewName() const { return viewName_; }
  bool portableActive() const { return active_; }

protected:
  bool active_;
  const char *viewName_;
};

class FileMuteGroup {
public:
  // Native arguments occupy r1/r2/r3, establishing an instance method. The
  // boolean source return is a port choice; original C++ return is unencoded.
  bool findAttribute(const Core::Portable::Attributes *attributes,
                     const char *path, const char *attribute);
};

class McuVpotControl : public Core::Portable::Slider {
public:
  McuVpotControl(const Core::TRect<int> &size,
                 Core::Portable::Parameter *parameter);
  struct PortableState {
    Core::Portable::Bitmap *image;
    Core::Portable::Bitmap *strip;
    Core::Portable::Bitmap *slice;
    int value;
  };
  PortableState portableState() const;

protected:
  Core::Portable::BitmapReference image_, strip_, slice_;
  int value_;
};
} // namespace Presonus
