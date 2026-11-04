#include "core/portable/gui/coregraphics.h"
#include "presonus/VUMeterControl.hpp"
#include "presonus/trial08/MixerComponentBase.hpp"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Presonus;
static void *watched = nullptr;
static int deleted = 0;
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == watched)
    ++deleted;
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (p == watched)
    ++deleted;
  __real__ZdlPvm(p, size);
}
const Core::Portable::ParamInfo numericInfo =
    PARAM_FLOAT(0, "mute", -1000, 1000, 0, 1, nullptr, nullptr, 0, 0);
struct Number : Core::Portable::NumericParam {
  Number() : NumericParam(numericInfo) {}
  int observers() const { return observerList.count(); }
};
struct CaptureGraphics : Core::Portable::ColorBitmapRenderer {
  Core::Portable::Bitmap *images[3];
  std::vector<int> calls;
  CaptureGraphics(Core::Portable::Bitmap &target, Core::Portable::Bitmap *a,
                  Core::Portable::Bitmap *b, Core::Portable::Bitmap *c)
      : ColorBitmapRenderer(target), images{a, b, c} {}
  bool drawBitmap(Core::PointRef point, Core::Portable::Bitmap &bitmap,
                  Core::RectRef rect,
                  const Core::Portable::BitmapMode *) override {
    int id = 0;
    while (images[id] != &bitmap)
      ++id;
    calls.insert(calls.end(), {id, point.x, point.y, rect.left, rect.top,
                               rect.right, rect.bottom});
    return true;
  }
};
int main() {
  {
    FileMuteGroup compatibility;
    Core::Portable::DefaultAllocatedAttributes attributes;
    attributes.set("present", 1);
    if (!compatibility.findAttribute(&attributes, "missing", "present"))
      return 5;
    bool guarded = false;
    try {
      compatibility.paramChanged(nullptr, 3);
    } catch (const std::logic_error &) {
      guarded = true;
    }
    if (!guarded)
      return 6;
  }
  std::string command;
  while (std::cin >> command) {
    if (command == "frame") {
      int old, count, options, dirty, frame;
      std::cin >> old >> count >> options >> dirty >> frame;
      VUMeterControl control(Core::TRect<int>(0, 0, 16, 32));
      control.portableBindFrameState(old, count, options, dirty);
      control.setFrame(frame);
      std::cout << control.portableState().previousValue << ' '
                << control.portableDirty() << '\n';
    } else if (command == "threshold") {
      int options, count;
      float value;
      std::cin >> options >> count >> value;
      Number parameter;
      parameter.setMin(0.f);
      parameter.setMax(1.f);
      parameter.setValue(value, false);
      VUMeterControl control(Core::TRect<int>(0, 0, 16, 32));
      control.setParameter(&parameter);
      float thresholds[32];
      for (int i = 0; i < count; ++i)
        std::cin >> thresholds[i];
      control.portableBindThresholds(thresholds, count);
      control.portableBindFrameState(-1, count ? count : 4, options, false);
      control.changeFrames();
      std::cout << control.portableState().previousValue << ' '
                << control.portableDirty() << '\n';
    } else if (command == "all") {
      int n;
      std::cin >> n;
      Mixer::MixerComponentBase mixer;
      AllMutesGroup group(mixer);
      presonus::mute_group_port::MixerData data;
      Number parameters[8];
      for (int i = 0; i < n; ++i) {
        parameters[i].setMax(1.f);
        data.allMutes.add(&parameters[i]);
      }
      group.portableBindMixerData(data);
      group.activate();
      std::cout << group.portableMemberCount();
      for (int i = 0; i < n; ++i)
        std::cout << ' ' << parameters[i].getValue();
      std::cout << '\n';
    } else if (command == "draw") {
      int mode, frame, options;
      std::cin >> mode >> frame >> options;
      Core::Portable::Bitmap target(16, 16), image(10, 40), strip(12, 80),
          slice(14, 120);
      image.setFrameCount(4);
      strip.setFrameCount(4);
      slice.setFrameCount(4);
      CaptureGraphics graphics(target, &image, &strip, &slice);
      PotControl control(Core::TRect<int>(0, 0, 16, 16));
      control.portableBindBitmaps(&image, &strip, &slice);
      control.portableBindDrawState(mode, frame, 4, options);
      Core::Portable::DrawEvent event(graphics, Core::TRect<int>(0, 0, 16, 16));
      control.draw(event);
      std::cout << graphics.calls.size() / 7;
      for (int x : graphics.calls)
        std::cout << ' ' << x;
      std::cout << '\n';
    } else if (command == "cache" || command == "cachef") {
      double a, b, c;
      std::cin >> a >> b >> c;
      Mixer::MixerComponentBase mixer;
      Number parameter, channels[3];
      FileMuteGroup group(Core::Portable::FileName("fixture"), &parameter,
                          mixer);
      presonus::mute_group_port::MixerData data;
      const char *names[] = {"a", "b", "c"};
      double values[] = {a, b, c};
      Core::Portable::DefaultAllocatedAttributes attributes;
      auto *parent = attributes.makeAttributes("input");
      for (int i = 0; i < 3; ++i) {
        data.channels.add({"input", names[i], &channels[i]});
        if (command == "cachef")
          parent->makeAttributes(names[i])->set("mute", values[i]);
        else
          parent->makeAttributes(names[i])->set("mute",
                                                static_cast<int>(values[i]));
      }
      group.portableBindMixerData(data);
      group.cacheMutes(attributes);
      std::cout << group.portableMemberCount() << '\n';
    } else if (command == "param") {
      int enabled, message;
      float value;
      std::cin >> enabled >> message >> value;
      Mixer::MixerComponentBase mixer;
      Number parameter;
      parameter.setMin(-2.f);
      parameter.setMax(2.f);
      parameter.setValue(value, false);
      FileMuteGroup group(Core::Portable::FileName("fixture"), &parameter,
                          mixer);
      group.portableSetReactivation(enabled);
      group.paramChanged(&parameter, message);
      std::cout << parameter.getValue() << ' ' << group.portableReactivation()
                << '\n';
    } else if (command == "basector") {
      Mixer::MixerComponentBase mixer;
      MuteGroupBase group(mixer);
      std::cout << group.portableMemberCount() << ' '
                << (group.portableMixer() == &mixer) << '\n';
    } else if (command == "allctor") {
      Mixer::MixerComponentBase mixer;
      AllMutesGroup group(mixer);
      std::cout << group.portableMemberCount() << ' '
                << (group.portableMixer() == &mixer) << '\n';
    } else if (command == "filector") {
      Mixer::MixerComponentBase mixer;
      Number parameter;
      int count = 0, identity = 0;
      {
        FileMuteGroup group(Core::Portable::FileName("fixture"), &parameter,
                            mixer);
        count = parameter.observers();
        identity = group.portableMixer() == &mixer;
      }
      std::cout << count << ' ' << parameter.observers() << ' ' << identity
                << '\n';
    } else if (command == "destroy") {
      std::string type;
      int deleting;
      std::cin >> type >> deleting;
      Mixer::MixerComponentBase mixer;
      Number parameter;
      deleted = 0;
      if (type == "base") {
        auto *p = new MuteGroupBase(mixer);
        watched = p;
        if (deleting)
          delete p;
        else {
          p->~MuteGroupBase();
          watched = nullptr;
          ::operator delete(p);
        }
      } else if (type == "all") {
        auto *p = new AllMutesGroup(mixer);
        watched = p;
        if (deleting)
          delete p;
        else {
          p->~AllMutesGroup();
          watched = nullptr;
          ::operator delete(p);
        }
      } else if (type == "file") {
        auto *p = new FileMuteGroup(Core::Portable::FileName("fixture"),
                                    &parameter, mixer);
        watched = p;
        if (deleting)
          delete p;
        else {
          p->~FileMuteGroup();
          watched = nullptr;
          ::operator delete(p);
        }
      } else if (type == "pot") {
        Core::Portable::Bitmap image, strip, slice;
        auto *p = new PotControl(Core::TRect<int>(0, 0, 16, 32));
        p->portableBindBitmaps(&image, &strip, &slice);
        watched = p;
        p->~PotControl();
        watched = nullptr;
        ::operator delete(p);
        std::cout << deleted << ' ' << image.isReferenced() << ' '
                  << strip.isReferenced() << ' ' << slice.isReferenced()
                  << '\n';
        continue;
      } else {
        Core::Portable::Bitmap image, strip, slice;
        auto *p = new VUMeterControl(Core::TRect<int>(0, 0, 16, 32));
        p->portableBindBitmaps(&image, &strip, &slice);
        watched = p;
        if (deleting)
          delete p;
        else {
          p->~VUMeterControl();
          watched = nullptr;
          ::operator delete(p);
        }
        std::cout << deleted << ' ' << image.isReferenced() << ' '
                  << strip.isReferenced() << ' ' << slice.isReferenced()
                  << '\n';
        watched = nullptr;
        continue;
      }
      std::cout << deleted << ' ' << parameter.observers() << '\n';
      watched = nullptr;
    } else if (command == "ctor") {
      VUMeterControl control(Core::TRect<int>(0, 0, 16, 32));
      auto s = control.portableState();
      std::cout << s.previousValue << ' ' << s.frameCount << ' ' << s.options
                << ' ' << control.portableDirty() << '\n';
    } else
      return 2;
  }
}
