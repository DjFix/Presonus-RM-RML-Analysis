#include "presonus/surface/MuteGroupsComponent.hpp"

#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>

namespace {
using Mute = Presonus::Surface::MuteGroupsComponent;
using Core::Portable::Component;
using Presonus::DelayTimer;
using presonus::timing::DelayTimerAccess;

struct BaseReceiver : Mute {
  static bool feedback(const Mute &mute) {
    const auto list = &BaseReceiver::paramList;
    return (mute.*list).isFeedbackNeeded();
  }
};

struct Timer {
  DelayTimer *pointer;
  float seconds;
};

std::array<Timer, 9> timers{};
std::size_t count = 0;
bool recordingConstruction = false;
bool recordingDestruction = false;
const void *receiver = nullptr;
const void *borrowedTimer = nullptr;
const void *backing = nullptr;
bool recordingBind = false;
std::int64_t ticks = 0;

void require(bool condition) {
  if (!condition)
    std::abort();
}

std::uint32_t bits(float x) {
  std::uint32_t result;
  std::memcpy(&result, &x, sizeof(x));
  return result;
}

void event(const char *verb, const void *pointer) {
  if (!recordingDestruction)
    return;
  require(!borrowedTimer || pointer != borrowedTimer);
  if (pointer == backing) {
    require(std::strcmp(verb, "free") == 0);
    std::puts("free:backing");
    return;
  }
  if (pointer == receiver) {
    std::printf("%s:receiver\n", verb);
    return;
  }
  for (std::size_t i = 0; i < count; ++i) {
    if (pointer == timers[i].pointer) {
      if (i == 0)
        std::printf("%s:refresh\n", verb);
      else
        std::printf("%s:%zu\n", verb, i - 1);
    }
  }
}

void checkTiming(DelayTimer &timer) {
  const auto initial = DelayTimerAccess::get(timer);
  ticks = 1000 * 1000000LL;
  timer.beginAction(-1.f);
  ticks += (initial.duration - 1) * 1000000;
  require(timer.isExecuting() && !timer.isLongEnoughYet());
  ticks += 1000000;
  require(timer.isLongEnoughYet() && timer.endAction());
  timer.reset();
}
} // namespace

extern "C" void
muteD0(Mute *) asm("_ZN8Presonus7Surface19MuteGroupsComponentD0Ev");
extern "C" void
muteD1(Mute *) asm("_ZN8Presonus7Surface19MuteGroupsComponentD1Ev");
extern "C" void
muteD2(Mute *) asm("_ZN8Presonus7Surface19MuteGroupsComponentD2Ev");

extern "C" void realTimerCtor(DelayTimer *,
                              float) asm("__real__ZN8Presonus10DelayTimerC1Ef");
extern "C" void
wrappedTimerCtor(DelayTimer *,
                 float) asm("__wrap__ZN8Presonus10DelayTimerC1Ef");
void wrappedTimerCtor(DelayTimer *timer, float seconds) {
  realTimerCtor(timer, seconds);
  if (recordingConstruction) {
    require(count < timers.size());
    timers[count++] = {timer, seconds};
  }
}

extern "C" void
realTimerDtor(DelayTimer *) asm("__real__ZN8Presonus10DelayTimerD1Ev");
extern "C" void
wrappedTimerDtor(DelayTimer *) asm("__wrap__ZN8Presonus10DelayTimerD1Ev");
void wrappedTimerDtor(DelayTimer *timer) {
  event("destroy", timer);
  realTimerDtor(timer);
}

extern "C" void
realBaseDtor(Component *) asm("__real__ZN4Core8Portable9ComponentD2Ev");
extern "C" void
wrappedBaseDtor(Component *) asm("__wrap__ZN4Core8Portable9ComponentD2Ev");
void wrappedBaseDtor(Component *base) {
  if (recordingDestruction && base == receiver)
    std::puts("base");
  realBaseDtor(base);
}

extern "C" void *realNew(std::size_t) asm("__real__Znwm");
extern "C" void *wrappedNew(std::size_t) asm("__wrap__Znwm");
void *wrappedNew(std::size_t size) {
  auto *ptr = realNew(size);
  if ((recordingConstruction && size == 8 * sizeof(DelayTimer *)) ||
      (recordingBind && size == 2 * sizeof(DelayTimer *)))
    backing = ptr;
  return ptr;
}

extern "C" void realDelete(void *) asm("__real__ZdlPv");
extern "C" void wrappedDelete(void *) asm("__wrap__ZdlPv");
void wrappedDelete(void *ptr) {
  realDelete(ptr);
  event("free", ptr);
}

extern "C" void realSizedDelete(void *, std::size_t) asm("__real__ZdlPvm");
extern "C" void wrappedSizedDelete(void *, std::size_t) asm("__wrap__ZdlPvm");
void wrappedSizedDelete(void *ptr, std::size_t size) {
  realSizedDelete(ptr, size);
  event("free", ptr);
}

extern "C" std::int64_t
wrappedClock() asm("__wrap__ZN8presonus4dice19packetClockRawTicksEv");
std::int64_t wrappedClock() { return ticks; }

int main(int argc, char **argv) {
  require(argc == 3);
  const char *variant = argv[1];
  const bool borrowed = std::strcmp(argv[2], "borrowed") == 0;
  const bool deleting = std::strcmp(variant, "D0") == 0;
  const bool c2 = std::strcmp(variant, "C2") == 0;
  const bool d2 = std::strcmp(variant, "D2") == 0;
  alignas(Mute) std::byte storage[sizeof(Mute)];
  alignas(BaseReceiver) std::byte baseStorage[sizeof(BaseReceiver)];
  recordingConstruction = true;
  Mute *mute = deleting   ? new Mute
               : c2 || d2 ? ::new (baseStorage) BaseReceiver
                          : ::new (storage) Mute;
  recordingConstruction = false;
  receiver = static_cast<Component *>(mute);
  require(std::strcmp(mute->getName(), "") == 0);
  std::printf("configuration %d %d\n", BaseReceiver::feedback(*mute),
              mute->getName()[0] == '\0');
  require(count == 9 && backing &&
          timers[0].pointer == &mute->muteRefreshTimer());
  for (std::size_t i = 0; i < count; ++i) {
    const auto [timer, seconds] = timers[i];
    const auto state = DelayTimerAccess::get(*timer);
    std::printf("timer %u %lld %lld %lld %u %d\n", bits(seconds),
                static_cast<long long>(state.start),
                static_cast<long long>(state.duration),
                static_cast<long long>(state.elapsed), bits(state.reciprocal),
                state.executing);
    checkTiming(*timer);
  }
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.maxValue = 1.f;
  for (int i = 0; i < 8; ++i) {
    info.tag = i;
    Core::Portable::NumericParam group(info);
    mute->paramChanged(&group, 0);
    for (int j = 0; j < 8; ++j)
      require(timers[j + 1].pointer->isExecuting() == (i == j));
    timers[i + 1].pointer->reset();
  }
  DelayTimer external(3.f);
  if (borrowed) {
    borrowedTimer = &external;
    const auto prior = backing;
    recordingBind = true;
    mute->bindMuteTimers({&external, nullptr});
    recordingBind = false;
    require(backing && backing != prior);
    info.tag = 0;
    Core::Portable::NumericParam group(info);
    mute->paramChanged(&group, 0);
    require(external.isExecuting() && !timers[1].pointer->isExecuting());
  }
  recordingDestruction = variant[0] == 'D';
  if (deleting)
    muteD0(mute);
  else if (d2)
    muteD2(mute);
  else
    muteD1(mute);
  recordingDestruction = false;
  if (borrowed)
    require(external.isExecuting() &&
            DelayTimerAccess::get(external).duration == 3000);
}
