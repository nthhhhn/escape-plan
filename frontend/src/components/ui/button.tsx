import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';
const variants = cva('inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 disabled:pointer-events-none disabled:opacity-40', {variants: {variant: {default: 'bg-[#ecc94b] text-[#181d22] hover:bg-[#ffdd65]', secondary: 'bg-white/10 text-white hover:bg-white/20', outline: 'border border-white/20 bg-transparent text-white hover:bg-white/10', destructive: 'bg-red-600 text-white hover:bg-red-500'}, size: {default: 'h-11 px-5', sm: 'h-9 px-3', icon: 'h-10 w-10'}}, defaultVariants: {variant: 'default', size: 'default'}});
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof variants> {asChild?: boolean}
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({className, variant, size, asChild=false, ...props}, ref) => {const Comp = asChild ? Slot : 'button'; return <Comp className={cn(variants({variant,size,className}))} ref={ref} {...props}/>;});
Button.displayName = 'Button';
