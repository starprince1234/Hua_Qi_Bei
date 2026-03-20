'use client';

interface ResultDisplayProps {
  result: any;
}

export default function ResultDisplay({ result }: ResultDisplayProps) {
  return <pre>{JSON.stringify(result, null, 2)}</pre>;
}
