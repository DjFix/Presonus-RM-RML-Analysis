#pragma once
namespace presonus::noaa {
struct RouterLookupImage;
// Independent shared helper. The original64-byte internal table is defined
// once in TCardRouterCommands.cpp; adjacent bytes remain explicit input.
unsigned char mapRouterChannel(unsigned char channel,
                               const RouterLookupImage &lookup);
} // namespace presonus::noaa
