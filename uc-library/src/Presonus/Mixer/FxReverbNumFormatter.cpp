#include "presonus/mixer/FxReverbNumFormatter.hpp"
#include "presonus/mixer/XmenFormatterInitializer.hpp"
namespace Presonus::Mixer {
FxReverbNumFormatter::~FxReverbNumFormatter() = default;
template <> void XmenFormatterInitializer::addClass<FxReverbNumFormatter>() {
  static FxReverbNumFormatter theFormatter(
      FxReverbNumFormatter::SourcePortTag{}, 'R');
  Core::FormatterRegistry::add(&theFormatter);
}

} // namespace Presonus::Mixer
