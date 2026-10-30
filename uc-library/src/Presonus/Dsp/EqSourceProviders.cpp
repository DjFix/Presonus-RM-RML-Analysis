#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include "Logarithm.hpp"
#include "presonus/mixer_dsp/AdditionalFormatters.hpp"
#include "presonus/mixer_dsp/Formatters.hpp"
#include "presonus/mixer_dsp/Interpolators.hpp"
#include <atomic>
#include <cmath>
#include <memory>
#include <mutex>
#include <stdexcept>
extern "C" float presonus_glibc29_expf(float);
namespace {
std::atomic<bool> ready{false};
std::once_flag bootstrapOnce;
class NamedGainSourceFormatter final : public Presonus::Dsp::GainFormatter {
public:
  NamedGainSourceFormatter()
      : Presonus::Dsp::GainFormatter(
            Presonus::Dsp::AdditionalFormatterSourceTag{}, 2, true) {
    // Exact name and arguments observed at genuine app initializer's Gain C1.
    // This named tagged adapter is independent; no original Gain C1 claim.
    name = "gain";
  }
};
struct ProviderObjects {
  NamedGainSourceFormatter gain;
  Presonus::Dsp::FreqFormatter frequency{false};
  Presonus::Dsp::FreqFormatter integerFrequency{true};
  Presonus::Dsp::EQQFormatter q;
};
ProviderObjects &providers() {
  static ProviderObjects objects;
  return objects;
}
Core::Interpolator *createSourceSkew() {
  // Explicit valid source-port seed; subsequent app setRange supplies all
  // measured EQ bounds. Not a recovered default Skew constructor declaration.
  const presonus::dsp::InterpolationState seed{0.f, 1.f, .5f, 0.f,
                                               1.f, 1.f, 1.f, 0.f};
  return new Presonus::Dsp::SkewInterpolator(
      presonus::dsp::InterpolationPortTag{}, seed);
}
Core::Interpolator *createSourceLog() {
  return new presonus::dsp::EqLogSourceInterpolator;
}
bool knownRange(float a, float b) {
  return (a == 36.f && b == 465.f) || (a == 90.f && b == 1200.f) ||
         (a == 380.f && b == 5000.f) || (a == 1400.f && b == 18000.f) ||
         (a == 20.f && b == 20000.f) || (a == 24.f && b == 1000.f) ||
         (a == 100.f && b == 20000.f) || (a == 40.f && b == 16000.f);
}
void checkFormatter(const char *name, const Core::Formatter *expected) {
  const auto *found = Core::FormatterRegistry::find(name);
  if (found && found != expected)
    throw std::logic_error("EQ source bootstrap: conflicting formatter name");
}
} // namespace
namespace presonus::dsp {
EqLogSourceInterpolator::EqLogSourceInterpolator()
    : Core::Interpolator(), logarithmicDomain_(0.f, 1.f) {}
EqLogSourceInterpolator::~EqLogSourceInterpolator() = default;
void EqLogSourceInterpolator::setRange(float minimum, float maximum,
                                       float midpoint) {
  supported_ = false;
  if (!std::isfinite(minimum) || !std::isfinite(maximum) ||
      !std::isfinite(midpoint) || midpoint != 0.f ||
      !knownRange(minimum, maximum))
    throw std::invalid_argument("EQ log source port: unsupported range");
  Core::Interpolator::setRange(minimum, maximum, midpoint);
  logarithmicDomain_.setRange(detail::sourceLogf(minimum),
                              detail::sourceLogf(maximum), 0.f);
  supported_ = true;
}
float EqLogSourceInterpolator::normalizedToRange(float value) const {
  if (!supported_ || !std::isfinite(value) || value < 0.f || value > 1.f)
    throw std::domain_error("EQ log source port: unsupported normalized input");
  if (value == 0.f)
    return minRange;
  if (value == 1.f)
    return maxRange;
  const float result =
      presonus_glibc29_expf(logarithmicDomain_.normalizedToRange(value));
  // Independent modern range bound, including quantized endpoint neighbors.
  return result < minRange ? minRange : result > maxRange ? maxRange : result;
}
float EqLogSourceInterpolator::rangeToNormalized(float value) const {
  // Independent modern Gate sentinel domain only: original app default20 is
  // below its observed [40,16000] range. Actual CCL logarithmic linear inverse
  // clamps log(20..40) to its lower endpoint. Other seven ranges stay strict.
  const bool gateSentinel =
      minRange == 40.f && maxRange == 16000.f && value >= 20.f && value < 40.f;
  if (!supported_ || !std::isfinite(value) ||
      (value < minRange && !gateSentinel) || value > maxRange)
    throw std::domain_error("EQ log source port: unsupported range input");
  if (value == minRange)
    return 0.f;
  if (value == maxRange)
    return 1.f;
  return logarithmicDomain_.rangeToNormalized(detail::sourceLogf(value));
}
void registerEqSourcePortProviders() {
  std::call_once(bootstrapOnce, [] {
    auto &objects = providers();
    checkFormatter("gain", &objects.gain);
    checkFormatter("freq", &objects.frequency);
    checkFormatter("freq.0", &objects.integerFrequency);
    checkFormatter("eqq", &objects.q);
    // CCL exposes no callback-inspection API. These explicit owned lookups may
    // invoke an existing factory; callers must bootstrap before registry use.
    std::unique_ptr<Core::Interpolator> oldSkew(
        Core::InterpolatorFactory::create("skew"));
    std::unique_ptr<Core::Interpolator> oldLog(
        Core::InterpolatorFactory::create("log"));
    if (oldSkew || oldLog)
      throw std::logic_error("EQ source bootstrap: conflicting factory name");
    Core::FormatterRegistry::add(&objects.gain);
    Core::FormatterRegistry::add(&objects.frequency);
    Core::FormatterRegistry::add(&objects.integerFrequency);
    Core::FormatterRegistry::add(&objects.q);
    Core::InterpolatorFactory::add("skew", createSourceSkew);
    Core::InterpolatorFactory::add("log", createSourceLog);
    std::unique_ptr<Core::Interpolator> skew(
        Core::InterpolatorFactory::create("skew"));
    std::unique_ptr<Core::Interpolator> log(
        Core::InterpolatorFactory::create("log"));
    if (!skew || !log ||
        Core::FormatterRegistry::find("gain") != &objects.gain ||
        Core::FormatterRegistry::find("freq") != &objects.frequency ||
        Core::FormatterRegistry::find("freq.0") != &objects.integerFrequency ||
        Core::FormatterRegistry::find("eqq") != &objects.q)
      throw std::runtime_error("EQ source bootstrap: registration unavailable");
    ready.store(true, std::memory_order_release);
  });
}
bool eqSourcePortProvidersReady() noexcept {
  return ready.load(std::memory_order_acquire);
}
} // namespace presonus::dsp
