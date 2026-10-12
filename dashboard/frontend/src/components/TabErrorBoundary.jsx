import React from 'react';
import { StateMessage } from './ui';

export default class TabErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('Dashboard tab failed', error, info);
  }

  render() {
    if (this.state.error) {
      return <StateMessage type="error">Tab này gặp lỗi khi render. Hãy chuyển tab hoặc tải lại trang.</StateMessage>;
    }
    return this.props.children;
  }
}
