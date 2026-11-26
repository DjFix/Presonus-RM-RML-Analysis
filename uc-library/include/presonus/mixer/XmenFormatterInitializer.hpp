#pragma once

namespace Presonus::Mixer {

class FxTypeFormatter;

class XmenFormatterInitializer {
public:
  template <class Formatter> static void addClass();
};

template <> void XmenFormatterInitializer::addClass<FxTypeFormatter>();

} // namespace Presonus::Mixer
