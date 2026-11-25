#include "presonus/dsp/ControllerProperties.hpp"
#include "presonus/dsp/LimiterController.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string_view>
#include <vector>

using Presonus::Dsp::LimiterController;
using Word = std::uint32_t;
using Words = std::vector<Word>;

namespace {
void *observedReceiver;
Words *lifecycle;

Word bits(float value) { return std::bit_cast<Word>(value); }
float number(Word value) { return std::bit_cast<float>(value); }
int signedWord(Word value) { return std::bit_cast<int>(value); }
Word unsignedWord(int value) { return std::bit_cast<Word>(value); }

void deleteStorage(void *pointer) noexcept {
  if (pointer && pointer == observedReceiver) {
    observedReceiver = nullptr;
    lifecycle->push_back(2);
  }
  std::free(pointer);
}
} // namespace

void operator delete(void *pointer) noexcept { deleteStorage(pointer); }
void operator delete(void *pointer, std::size_t) noexcept {
  deleteStorage(pointer);
}
void *operator new(std::size_t size) {
  if (void *pointer = std::malloc(size ? size : 1))
    return pointer;
  throw std::bad_alloc();
}

namespace {
class Handler : public Core::IPropertyHandler {
public:
  explicit Handler(Words &events, bool deleteOnRelease = false)
      : events_(events), deleteOnRelease_(deleteOnRelease) {}
  void setProperty(const Core::Property &property) override {
    if (property.size != 24)
      std::abort();
    std::array<Word, 6> payload{};
    std::memcpy(payload.data(), &property, sizeof(payload));
    events_.insert(events_.end(), payload.begin(), payload.end());
  }
  void getProperty(Core::Property &) override {}
  void release() override {
    events_.push_back(1);
    if (deleteOnRelease_)
      delete this;
  }

private:
  Words &events_;
  bool deleteOnRelease_;
};

struct DerivedLimiter : LimiterController {
  explicit DerivedLimiter(int id) : LimiterController(id) {}
  ~DerivedLimiter() override;
};
DerivedLimiter::~DerivedLimiter() = default;

void appendFields(LimiterController &limiter, Words &result) {
  const auto &state = limiter.portableLimiterState();
  result.insert(result.end(),
                {limiter.sourceState().processDirty, state.enabled,
                 bits(state.thresholdAmplitude), bits(state.smoothing),
                 bits(state.reductionAmplitude)});
}

void seed(LimiterController &limiter, const Word *input) {
  limiter.sourceState().processDirty = static_cast<std::uint8_t>(input[0]);
  limiter.portableLimiterState() = {input[1], number(input[2]),
                                    number(input[3]), number(input[4])};
}

Words run(std::string_view mode, const Words &input) {
  Words result;
  if (mode == "d0" || mode == "d1") {
    const bool deleting = mode == "d0";
    alignas(LimiterController) std::byte storage[sizeof(LimiterController)];
    Presonus::Dsp::IController *limiter = deleting ? new LimiterController(0)
                                                   : ::new (storage)
                                                         LimiterController(0);
    auto *handler = input[0] ? new Handler(result, true) : nullptr;
    limiter->setTarget(handler);
    if (input[1])
      static_cast<LimiterController *>(limiter)->makeTargetOwner();
    lifecycle = &result;
    observedReceiver = limiter;
    if (deleting)
      limiter->release();
    else
      static_cast<LimiterController *>(limiter)->~LimiterController();
    if (deleting == (observedReceiver != nullptr))
      std::abort();
    if (!input[1])
      delete handler;
    observedReceiver = nullptr;
    lifecycle = nullptr;
    return result;
  }
  if (mode == "c1" || mode == "c2") {
    alignas(DerivedLimiter) std::byte storage[sizeof(DerivedLimiter)];
    LimiterController *limiter =
        mode == "c2" ? ::new (storage) DerivedLimiter(signedWord(input[0]))
                     : ::new (storage) LimiterController(signedWord(input[0]));
    auto &state = limiter->sourceState();
    result.push_back(unsignedWord(state.constructorId));
    appendFields(*limiter, result);
    result.push_back(unsignedWord(state.descriptors->count()));
    for (int i = 0; i < state.descriptors->count(); ++i) {
      const auto &descriptor = state.descriptors->at(i)->sourceState();
      result.push_back(unsignedWord(descriptor.tag));
      result.push_back(descriptor.word14);
    }
    if (mode == "c2")
      static_cast<DerivedLimiter *>(limiter)->~DerivedLimiter();
    else
      limiter->~LimiterController();
    return result;
  }
  Handler handler(result);
  LimiterController limiter(0);
  if (mode == "get") {
    seed(limiter, &input[1]);
    result.push_back(bits(limiter.getValue(signedWord(input[0]))));
  } else if (mode == "set") {
    seed(limiter, &input[2]);
    limiter.setValue(signedWord(input[0]), number(input[1]));
  } else if (mode == "update") {
    seed(limiter, &input[3]);
    limiter.sourceState().word04 = input[1];
    limiter.sourceState().processRateBits = input[2];
    if (input[0])
      limiter.setTarget(&handler);
    limiter.doUpdates();
    Words state;
    appendFields(limiter, state);
    result.insert(result.begin(), state.begin(), state.end());
    return result;
  } else {
    std::abort();
  }
  appendFields(limiter, result);
  return result;
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::size_t count;
  while (std::cin >> count) {
    Words input(count);
    for (auto &value : input)
      if (!(std::cin >> value))
        return 2;
    auto result = run(argv[1], input);
    std::cout << result.size();
    for (Word value : result)
      std::cout << ' ' << value;
    std::cout << '\n';
  }
  return std::cin.eof() ? 0 : 2;
}
