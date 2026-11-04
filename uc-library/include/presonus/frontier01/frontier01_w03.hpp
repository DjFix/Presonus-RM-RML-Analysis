#pragma once

#include "core/portable/corecomponent.h"
#include "core/portable/corefilename.h"
#include "core/portable/gui/corecontrols.h"
#include "presonus/MuteGroupBase.hpp"

// Partial source ports. Native base-constructor calls establish these provider
// relationships. These declarations do not establish firmware layouts or ABI.
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

class AllMutesGroup : public MuteGroupBase {
public:
  explicit AllMutesGroup(Mixer::MixerComponentBase &mixer);
  ~AllMutesGroup() override;
  void activate();
};

class FileMuteGroup : public MuteGroupBase, public Core::Portable::Component {
public:
  // Independent template compatibility API for earlier findAttribute callers.
  // No recovered original default-constructor identity is claimed.
  template <
      class Compatibility = presonus::mute_group_port::UnboundCompatibility>
  FileMuteGroup()
      : MuteGroupBase(Compatibility{}), Core::Portable::Component(""),
        parameter_(nullptr) {}
  FileMuteGroup(Core::Portable::FileName filename,
                Core::Portable::Parameter *parameter,
                Mixer::MixerComponentBase &mixer);
  ~FileMuteGroup() override;
  void paramChanged(Core::Portable::Parameter *parameter, int message) override;
  void cacheMutes(const Core::Portable::Attributes &attributes);
  void portableSetReactivation(bool value) { reactivate_ = value; }
  bool portableReactivation() const { return reactivate_; }
  const Core::Portable::FileName &portableFilename() const { return filename_; }
  // Native arguments occupy r1/r2/r3, establishing an instance method. The
  // boolean source return is a port choice; original C++ return is unencoded.
  bool findAttribute(const Core::Portable::Attributes *attributes,
                     const char *path, const char *attribute);

private:
  bool storing_ = false, reactivate_ = false;
  Core::Portable::FileName filename_;
  Core::Portable::Parameter *parameter_;
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
