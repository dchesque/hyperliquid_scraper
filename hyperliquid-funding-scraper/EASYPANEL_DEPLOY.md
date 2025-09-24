# 🚀 Deploy no EasyPanel - Fix do Erro

## ❌ Problema Identificado
O erro ocorreu devido a dependências obsoletas no Dockerfile original. Foi criada uma versão simplificada.

## ✅ Solução Implementada

### 1. **Dockerfile Simplificado**
Substituído por versão minimalista que só instala o necessário:
- Chrome via repositório oficial
- ChromeDriver compatível automaticamente
- Dependências Python apenas

### 2. **Arquivos para Upload**
Certifique-se de que estes arquivos estão no seu EasyPanel:

```
├── Dockerfile (novo, simplificado)
├── requirements.txt
├── src/ (pasta completa)
├── migrations/ (pasta completa)
├── .env.production → rename para .env
└── .dockerignore (opcional)
```

## 🔧 Passos para Deploy Correto

### **Passo 1: Preparar Environment**
No EasyPanel, configure as variáveis de ambiente:

```env
# OBRIGATÓRIO - Suas credenciais Supabase
SUPABASE_URL=https://ioabuukbxdzceixorqzp.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlvYWJ1dWtieGR6Y2VpeG9ycXpwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg2ODAzODksImV4cCI6MjA3NDI1NjM4OX0.N38uSuPcuj60gpsWv-ATMhQLDTa2xWBTxvmJo4vKxdQ

# Configuração de produção
HEADLESS_MODE=true
RUN_INTERVAL_MINUTES=10
ENABLE_SCHEDULER=true
ENVIRONMENT=production
TZ=America/Sao_Paulo
LOG_LEVEL=INFO

# Chrome config
CHROME_DRIVER_PATH=/usr/local/bin/chromedriver
USER_AGENT=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36

# Performance
SCRAPING_TIMEOUT=45
RETRY_ATTEMPTS=3
PAGE_LOAD_WAIT=15
MAX_WORKERS=3
BATCH_INSERT_SIZE=25
```

### **Passo 2: Deploy no EasyPanel**

1. **Criar Novo Projeto** no EasyPanel
2. **Source**: GitHub/Upload dos arquivos
3. **Build Method**: Dockerfile
4. **Environment Variables**: Adicionar as variáveis acima
5. **Port**: 8080 (opcional, para monitoring)
6. **Deploy**

### **Passo 3: Verificar Deploy**

Após o deploy bem-sucedido:

```bash
# URLs para testar (substitua pelo seu domínio)
http://seu-dominio.com:8080/health
http://seu-dominio.com:8080/api/status
```

## 🔍 Monitoramento

### **Logs no EasyPanel**
```bash
# Ver logs em tempo real
docker logs -f container-name

# Ver últimas 100 linhas
docker logs --tail=100 container-name
```

### **Verificar Funcionamento**
```bash
# Teste de conexão database
curl http://seu-dominio:8080/health

# Status da aplicação
curl http://seu-dominio:8080/api/status
```

## ⚡ Recursos Recomendados VPS

```yaml
# Mínimo
RAM: 1GB
CPU: 1 core
Storage: 10GB

# Recomendado
RAM: 2GB
CPU: 2 cores
Storage: 20GB
```

## 🛟 Troubleshooting

### **Se o build falhar novamente:**
1. Verificar se todos os arquivos foram enviados
2. Confirmar variáveis de ambiente no EasyPanel
3. Verificar logs de build no EasyPanel
4. Tentar deploy com Dockerfile.simple se disponível

### **Se o container não iniciar:**
1. Verificar credenciais Supabase
2. Confirmar se o banco de dados está acessível
3. Verificar logs do container
4. Testar conexão de rede

### **Se não coletar dados:**
1. Verificar logs: `docker logs container-name`
2. Testar manualmente: `docker exec -it container-name python -m src.main --run-once`
3. Verificar se o site target está acessível
4. Confirmar configurações de Chrome/ChromeDriver

## 📞 Comandos Úteis EasyPanel

```bash
# Rebuild forçado
docker build --no-cache .

# Restart container
docker restart container-name

# Shell access
docker exec -it container-name /bin/bash

# Ver recursos
docker stats container-name
```

---

## ✅ Checklist de Sucesso

- [ ] Dockerfile simplificado utilizado
- [ ] Variáveis de ambiente configuradas no EasyPanel
- [ ] Credenciais Supabase válidas
- [ ] Build completo sem erros
- [ ] Container iniciando corretamente
- [ ] Health check retornando 200 OK
- [ ] Dados sendo coletados e salvos no Supabase

**Agora o deploy deve funcionar perfeitamente! 🎉**