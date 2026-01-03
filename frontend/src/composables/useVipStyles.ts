// VIP styles composable

// VIP colors configuration
const VIP_COLORS = {
  3: 'rgb(225, 191, 43)',
  2: 'rgb(53, 221, 247)',
  1: 'rgb(84, 238, 89)',
  0: 'rgb(109, 109, 109)'
} as const;

export function useVipStyles() {
  const getVipStyle = (vipLevel: number) => {
    const color = VIP_COLORS[vipLevel as keyof typeof VIP_COLORS] || VIP_COLORS[0];
    return {
      color: color,
      fontWeight: 'bold'
    };
  };

  const getVipColor = (vipLevel: number) => {
    return VIP_COLORS[vipLevel as keyof typeof VIP_COLORS] || VIP_COLORS[0];
  };

  return {
    getVipStyle,
    getVipColor,
    VIP_COLORS
  };
}